from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from ..config import settings
from ..schemas.domain import (
    CalculationBreakdown,
    PlatformConfigInput,
    ProductInput,
    ProfitAnalysisRequest,
    ProfitResult,
    PromotionActivityInput,
)

CENT = Decimal("0.01")
ZERO = Decimal("0")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


class ProfitEngine:
    """Deterministic, Decimal-based source of truth for all financial calculations."""

    def calculate(self, request: ProfitAnalysisRequest) -> ProfitResult:
        p, c, a = request.product, request.platform_config, request.activity
        assumptions: list[str] = []
        if c.demo_default:
            assumptions.append("平台费率使用 DEMO DEFAULT，请按实际店铺协议核对")
        platform_rate = a.platform_commission_rate if a.platform_commission_rate is not None else c.platform_commission_rate
        creator_rate = a.creator_commission_rate if a.creator_commission_rate is not None else c.creator_commission_rate
        return_rate = a.return_rate_override if a.return_rate_override is not None else c.return_rate
        shipping = a.seller_shipping_cost if a.seller_shipping_cost is not None else c.shipping_cost
        if a.platform_commission_rate is None:
            assumptions.append("平台佣金率采用商品平台配置")
        if a.return_rate_override is None:
            assumptions.append("退货率采用商品平台配置")

        selling_price, discount_amount = self._selling_price(c.original_price, a)
        coupon = a.coupon_amount if a.coupon_cost_bearer.lower() in {"seller", "shared"} else ZERO
        if a.coupon_cost_bearer.lower() == "shared":
            coupon /= Decimal("2")
            assumptions.append("共同承担优惠券按卖家承担 50% 估算")

        tariff_base = p.purchase_cost if c.tariff_basis == "product_cost" else selling_price
        return_exposure = (
            c.return_shipping_nonrecoverable
            + p.packaging_cost
            + p.purchase_cost * c.return_product_loss_rate
            + selling_price * c.platform_nonrefundable_fee_rate
        )
        raw_costs = [
            ("平台佣金", selling_price * platform_rate, "活动售价 × 平台佣金率", {"售价": selling_price, "费率": platform_rate}, "平台按成交额收取的佣金"),
            ("活动额外佣金", selling_price * a.extra_commission_rate, "活动售价 × 活动额外佣金率", {"售价": selling_price, "费率": a.extra_commission_rate}, "参加活动新增的变动费用"),
            ("达人佣金", selling_price * creator_rate, "活动售价 × 达人佣金率", {"售价": selling_price, "费率": creator_rate}, "联盟达人带货佣金"),
            ("采购成本", p.purchase_cost, "商品采购成本", {"采购成本": p.purchase_cost}, "单件采购成本"),
            ("包装成本", p.packaging_cost, "单件包装成本", {"包装成本": p.packaging_cost}, "包装材料与操作成本"),
            ("物流成本", shipping, "平台配置或活动覆盖物流成本", {"物流": shipping}, "卖家承担的履约物流"),
            ("关税", tariff_base * c.tariff_rate, f"{'采购成本' if c.tariff_basis == 'product_cost' else '活动售价'} × 关税率", {"计税基数": tariff_base, "费率": c.tariff_rate}, "可配置计税策略"),
            ("支付手续费", selling_price * c.payment_fee_rate, "活动售价 × 支付费率", {"售价": selling_price, "费率": c.payment_fee_rate}, "支付通道费用"),
            ("汇率损耗", selling_price * c.fx_loss_rate, "活动售价 × 汇损率", {"售价": selling_price, "费率": c.fx_loss_rate}, "结算与换汇损耗"),
            ("退货风险准备金", return_rate * return_exposure, "退货率 × (不可回收运费 + 包装 + 商品损耗 + 不退平台费)", {"退货率": return_rate, "风险暴露": return_exposure}, "不是销售额简单乘退货率，而是按不可回收成本计提"),
            ("其他可变费用", c.other_variable_cost, "商品平台配置", {"其他费用": c.other_variable_cost}, "仓储、操作等其他单件费用"),
            ("卖家优惠券", coupon, "卖家承担的优惠券金额", {"优惠券": coupon}, "平台承担部分不计入卖家成本"),
        ]
        breakdown = [CalculationBreakdown(item=n, amount=money(v), formula=f, input_values=iv, description=d) for n, v, f, iv, d in raw_costs]
        subsidies = a.platform_subsidy + a.shipping_subsidy
        breakdown.append(CalculationBreakdown(item="平台及物流补贴", amount=money(-subsidies), formula="-(平台补贴 + 物流补贴)", input_values={"平台补贴": a.platform_subsidy, "物流补贴": a.shipping_subsidy}, description="补贴抵减卖家成本"))
        total_cost_raw = sum((v for _, v, *_ in raw_costs), ZERO) - subsidies
        unit_profit_raw = selling_price - total_cost_raw
        fixed_cost = a.fixed_cost
        displayed_unit_profit = money(unit_profit_raw)
        displayed_selling_price = money(selling_price)
        estimated_total_raw = displayed_unit_profit * a.estimated_sales - fixed_cost
        margin_raw = unit_profit_raw / selling_price if selling_price > ZERO else ZERO
        break_even = self.break_even_price(request)
        be_qty = None
        if fixed_cost > ZERO and unit_profit_raw > ZERO:
            be_qty = int((fixed_cost / unit_profit_raw).to_integral_value(rounding=ROUND_CEILING))
        risk_level, risk_label = self._risk(margin_raw)
        return ProfitResult(
            original_price=money(c.original_price), discount_amount=money(discount_amount), selling_price=displayed_selling_price, revenue=displayed_selling_price,
            total_cost=money(total_cost_raw), unit_profit=displayed_unit_profit, profit_margin=rate(margin_raw), estimated_sales=a.estimated_sales,
            estimated_revenue=money(displayed_selling_price * a.estimated_sales), estimated_total_profit=money(estimated_total_raw), break_even_price=break_even,
            break_even_quantity=be_qty, fixed_cost=money(fixed_cost), risk_level=risk_level, risk_label=risk_label, assumptions=assumptions, breakdown=breakdown,
        )

    def _selling_price(self, original: Decimal, activity: PromotionActivityInput) -> tuple[Decimal, Decimal]:
        if activity.discount_type == "percentage":
            discount = original * activity.discount_value
            return original - discount, discount
        if activity.discount_type == "fixed_amount":
            discount = min(original, activity.discount_value)
            return original - discount, discount
        if activity.discount_type == "fixed_price":
            price = max(ZERO, activity.discount_value)
            return price, original - price
        return original, ZERO

    def break_even_price(self, request: ProfitAnalysisRequest) -> Decimal | None:
        p, c, a = request.product, request.platform_config, request.activity
        platform_rate = a.platform_commission_rate if a.platform_commission_rate is not None else c.platform_commission_rate
        creator_rate = a.creator_commission_rate if a.creator_commission_rate is not None else c.creator_commission_rate
        return_rate = a.return_rate_override if a.return_rate_override is not None else c.return_rate
        shipping = a.seller_shipping_cost if a.seller_shipping_cost is not None else c.shipping_cost
        coupon = a.coupon_amount * (Decimal("0.5") if a.coupon_cost_bearer == "shared" else Decimal("1")) if a.coupon_cost_bearer in {"seller", "shared"} else ZERO
        variable_rate = platform_rate + a.extra_commission_rate + creator_rate + c.payment_fee_rate + c.fx_loss_rate
        fixed_unit = p.purchase_cost + p.packaging_cost + shipping + c.other_variable_cost + coupon - a.platform_subsidy - a.shipping_subsidy
        if c.tariff_basis == "product_cost":
            fixed_unit += p.purchase_cost * c.tariff_rate
        else:
            variable_rate += c.tariff_rate
        fixed_unit += return_rate * (c.return_shipping_nonrecoverable + p.packaging_cost + p.purchase_cost * c.return_product_loss_rate)
        variable_rate += return_rate * c.platform_nonrefundable_fee_rate
        denominator = Decimal("1") - variable_rate
        if denominator <= ZERO:
            return None
        return money(fixed_unit / denominator)

    def _risk(self, margin: Decimal) -> tuple[str, str]:
        labels = {"HIGHLY_RECOMMENDED": "强烈推荐", "RECOMMENDED": "可以参加", "CAUTION": "谨慎参加", "NOT_RECOMMENDED": "不建议参加"}
        for key, threshold in settings.risk_thresholds:
            if margin >= threshold:
                return key, labels[key]
        return "LOSS", "明确亏损"
