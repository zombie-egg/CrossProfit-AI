from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum

from ...schemas.domain import ProfitAnalysisRequest
from ..profit_engine import ProfitEngine, money, rate
from .base import SettlementLine
from .mapper import normalize_fees


class DiffReason(StrEnum):
    REFUND_TIMING = "REFUND_TIMING"
    SUBSIDY = "SUBSIDY"
    TAX = "TAX"
    ROUNDING = "ROUNDING"
    FX = "FX"
    RATE_ERROR = "RATE_ERROR"
    FEE_ATTRIBUTION = "FEE_ATTRIBUTION"
    UNMAPPED = "UNMAPPED"
    UNKNOWN = "UNKNOWN"


RATE_ITEMS = {"平台佣金", "活动额外佣金", "达人佣金", "支付手续费"}
VERIFIABLE_ITEMS = RATE_ITEMS | {"物流成本", "关税", "汇率损耗", "其他可变费用", "卖家优惠券", "平台及物流补贴"}


def _reason(name: str, diff: Decimal, currency_mismatch: bool, refunded: bool, rounding_explained: bool = False) -> DiffReason:
    if currency_mismatch:
        return DiffReason.FX
    if abs(diff) <= Decimal("0.01") or rounding_explained:
        return DiffReason.ROUNDING
    if refunded and name in RATE_ITEMS:
        return DiffReason.REFUND_TIMING
    if name == "平台及物流补贴":
        return DiffReason.SUBSIDY
    if name == "关税":
        return DiffReason.TAX
    if name == "汇率损耗":
        return DiffReason.FX
    if name == "退货风险准备金":
        return DiffReason.REFUND_TIMING
    if name in RATE_ITEMS:
        return DiffReason.RATE_ERROR
    if name in {"物流成本", "其他可变费用", "卖家优惠券"}:
        return DiffReason.FEE_ATTRIBUTION
    return DiffReason.UNKNOWN


class ReconciliationEngine:
    def run(self, snapshot_data: dict, lines: list[SettlementLine], fee_mapping: dict[str, str], unrecognized_columns: list[str] | None = None) -> dict:
        forecast = ProfitAnalysisRequest.model_validate(snapshot_data)
        sku = forecast.product.sku
        currency = forecast.activity.currency.upper()
        grouped: dict[tuple[str, str], list[SettlementLine]] = defaultdict(list)
        for line in lines:
            grouped[(line.order_id, line.sku)].append(line)
        differences: list[dict] = []
        unmapped: list[dict] = []
        unmatched_orders: list[dict] = []
        unverified_fees: list[dict] = []
        matched_units = 0
        returned_units = 0
        for (order_id, line_sku), group in grouped.items():
            if line_sku != sku:
                unmatched_orders.append({"order_id": order_id, "sku": line_sku, "reason": "SKU 与快照不符"})
                continue
            currencies = {line.currency for line in group}
            if len(currencies) != 1:
                unmatched_orders.append({"order_id": order_id, "sku": line_sku, "reason": "同一订单包含多种币种"})
                continue
            actual_currency = next(iter(currencies))
            currency_mismatch = actual_currency != currency
            qty = sum(line.quantity for line in group)
            gross = sum((line.gross_revenue for line in group), Decimal("0"))
            refund = sum((line.refund_amount for line in group), Decimal("0"))
            subsidy = sum((line.subsidy_amount for line in group), Decimal("0"))
            actual_fees: dict[str, Decimal] = {}
            for line in group:
                mapped, unknown = normalize_fees(line, fee_mapping)
                unmapped.extend({**item, "reason": DiffReason.UNMAPPED.value} for item in unknown)
                for name, value in mapped.items():
                    actual_fees[name] = actual_fees.get(name, Decimal("0")) + value
            if subsidy:
                actual_fees["平台及物流补贴"] = actual_fees.get("平台及物流补贴", Decimal("0")) - subsidy
            if gross < 0:
                unmatched_orders.append({"order_id": order_id, "sku": line_sku, "reason": "负收入调整项，需要人工归属"})
                continue
            matched_units += qty
            if refund > 0:
                returned_units += qty
            same_inputs = forecast.model_copy(deep=True)
            unit_price = money(gross / Decimal(qty))
            rounding_residual = gross - unit_price * qty
            same_inputs.platform_config.original_price = unit_price
            same_inputs.activity.discount_type = "none"
            same_inputs.activity.discount_value = Decimal("0")
            same_inputs.activity.platform_subsidy = money(subsidy / Decimal(qty))
            same_inputs.activity.shipping_subsidy = Decimal("0")
            same_inputs.activity.return_rate_override = Decimal("1") if refund > 0 else Decimal("0")
            same_inputs.activity.estimated_sales = qty
            expected = {item.item: item.amount * qty for item in ProfitEngine().calculate(same_inputs).breakdown}
            for name in VERIFIABLE_ITEMS - actual_fees.keys():
                if expected.get(name, Decimal("0")) != 0:
                    unverified_fees.append({"order_id": order_id, "sku": sku, "fee_item": name,
                        "predicted": str(expected[name]), "reason": "结算单未提供可核对费项"})
            for name, actual in actual_fees.items():
                if name not in expected:
                    unmapped.append({"order_id": order_id, "sku": sku, "fee_name": name, "amount": str(actual)})
                    continue
                predicted = expected[name]
                diff = actual - predicted
                fee_rate = {
                    "平台佣金": same_inputs.activity.platform_commission_rate if same_inputs.activity.platform_commission_rate is not None else same_inputs.platform_config.platform_commission_rate,
                    "活动额外佣金": same_inputs.activity.extra_commission_rate,
                    "达人佣金": same_inputs.activity.creator_commission_rate if same_inputs.activity.creator_commission_rate is not None else same_inputs.platform_config.creator_commission_rate,
                    "支付手续费": same_inputs.platform_config.payment_fee_rate,
                    "汇率损耗": same_inputs.platform_config.fx_loss_rate,
                }.get(name)
                if name == "关税" and same_inputs.platform_config.tariff_basis == "selling_price":
                    fee_rate = same_inputs.platform_config.tariff_rate
                rounding_explained = bool(rounding_residual and fee_rate is not None and abs(actual - money(gross * fee_rate)) <= Decimal("0.01"))
                reason = _reason(name, diff, currency_mismatch, refund > 0, rounding_explained)
                differences.append({"order_id": order_id, "sku": sku, "fee_item": name,
                    "predicted": str(predicted), "actual": str(actual),
                    "absolute_diff": str(abs(diff).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                    "relative_diff": str(rate(diff / predicted)) if predicted else None,
                    "reason": reason.value,
                    "revenue_rounding_residual": str(rounding_residual),
                    "currency": actual_currency,
                    "formula_pass": not currency_mismatch and abs(diff) <= Decimal("0.01")})
        estimated = forecast.activity.estimated_sales
        predicted_return = forecast.activity.return_rate_override if forecast.activity.return_rate_override is not None else forecast.platform_config.return_rate
        actual_return = rate(Decimal(returned_units) / Decimal(matched_units)) if matched_units else None
        forecast_diff = {"estimated_sales": estimated, "actual_sales": matched_units, "sales_delta": matched_units - estimated,
            "predicted_return_rate": str(predicted_return), "actual_return_rate": str(actual_return) if actual_return is not None else None,
            "return_rate_delta": str(rate(actual_return - predicted_return)) if actual_return is not None else None,
            "returned_units": returned_units,
            "note": "预测偏差独立于公式正确性；退款窗口未结束时退货率仍可能变化。有退款金额的订单 SKU 暂将全部件数计为退货。"}
        max_diff = max((Decimal(row["absolute_diff"]) for row in differences), default=Decimal("0"))
        if any(not row["formula_pass"] and row["reason"] != DiffReason.ROUNDING.value for row in differences):
            verdict = "FAIL"
        elif unmatched_orders or unmapped or unrecognized_columns or unverified_fees or not differences or any(not row["formula_pass"] for row in differences):
            verdict = "PARTIAL"
        else:
            verdict = "PASS"
        return {"formula_verdict": verdict, "max_fee_diff": str(max_diff), "forecast_diff": forecast_diff,
            "diff_data": {"fee_diffs": differences, "unmapped_fees": unmapped, "unmatched_orders": unmatched_orders,
                "unrecognized_columns": unrecognized_columns or [],
                "unverified_fees": unverified_fees,
                "assumptions": ["结算单 gross_revenue 按订单 SKU 的总成交额解释，并按 quantity 摊至单件；无订单 ID 的事前快照按 SKU 关联订单。", "采购、包装等结算单缺失的内部成本不计入公式通过判定。"]}}
