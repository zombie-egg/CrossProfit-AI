from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.services.reconciliation.base import SettlementLine, SettlementParseError
from backend.app.services.reconciliation.tiktok import TikTokSettlementParser
from backend.app.services.reconciliation.amazon import AmazonSettlementParser
from backend.app.services.reconciliation.mapper import normalize_fees
from backend.app.services.reconciliation.engine import ReconciliationEngine


FIXTURE = Path(__file__).parent / "fixtures" / "settlement_sample.csv"
MULTI_FIXTURE = Path(__file__).parent / "fixtures" / "settlement_multi_unit.csv"
MAPPING = {"fields": {"order_id": "Order", "sku": "SKU", "settled_at": "Settled", "currency": "Currency", "gross_revenue": "Gross", "refund_amount": "Refund", "subsidy_amount": "Subsidy"}, "fee_columns": {"Commission": "Commission", "Other": "Other"}}


@pytest.mark.parametrize("parser", [TikTokSettlementParser(), AmazonSettlementParser()])
def test_csv_parser_configurable_columns_and_unknowns(parser):
    lines, unknown = parser.parse(FIXTURE.read_bytes(), MAPPING)
    assert len(lines) == 2
    assert unknown == []
    assert lines[0].gross_revenue == Decimal("100.00")
    ignored_mapping = {**MAPPING, "ignored_columns": ["Other"], "fee_columns": {"Commission": "Commission"}}
    assert parser.parse(FIXTURE.read_bytes(), ignored_mapping)[1] == []
    with pytest.raises(SettlementParseError, match="未识别的列"):
        parser.parse(FIXTURE.read_bytes(), {"fields": {"order_id": "wrong"}})
    gbk = "订单,SKU,日期,币种,收入\n一,PB-001,2026-09-01,USD,1.00\n".encode("gbk")
    assert parser.parse(gbk, {"fields": {"order_id": "订单", "sku": "SKU", "settled_at": "日期", "currency": "币种", "gross_revenue": "收入"}})[0][0].order_id == "一"
    signed = "Order,SKU,Settled,Currency,Gross,Commission\no-3,PB-001,2026/09/01,USD,100,-10\n".encode("utf-8-sig")
    signed_mapping = {"fields": {"order_id": "Order", "sku": "SKU", "settled_at": "Settled", "currency": "Currency", "gross_revenue": "Gross"},
        "fee_columns": {"Commission": "Commission"}, "fee_signs": {"Commission": -1}, "date_format": "%Y/%m/%d"}
    assert parser.parse(signed, signed_mapping)[0][0].fee_items["Commission"] == Decimal("10")
    with pytest.raises(SettlementParseError, match="第 2 行"):
        parser.parse(signed.replace(b"100,-10", b"bad,-10"), signed_mapping)


def test_fee_normalization_preserves_unknown():
    line = TikTokSettlementParser().parse(FIXTURE.read_bytes(), MAPPING)[0][0]
    mapped, unknown = normalize_fees(line, {"Commission": "平台佣金"})
    assert mapped == {"平台佣金": Decimal("10.00")}
    assert unknown[0]["fee_name"] == "Other"
    assert unknown[0]["amount"] == "0.40"


def test_reconciliation_separates_formula_and_forecast(base_request):
    base_request.platform_config.platform_commission_rate = Decimal("0.10")
    base_request.activity.discount_type = "none"
    base_request.activity.extra_commission_rate = Decimal("0")
    lines, _ = TikTokSettlementParser().parse(FIXTURE.read_bytes(), MAPPING)
    result = ReconciliationEngine().run(base_request.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    assert result["formula_verdict"] == "PARTIAL"
    assert result["forecast_diff"]["actual_sales"] == 1
    assert result["forecast_diff"]["sales_delta"] == -499
    assert result["diff_data"]["fee_diffs"][0]["formula_pass"] is True
    assert result["diff_data"]["unmapped_fees"][0]["fee_name"] == "Other"
    assert result["diff_data"]["unmatched_orders"][0]["sku"] == "OTHER"
    lines[0].fee_items["Commission"] = Decimal("12")
    failed = ReconciliationEngine().run(base_request.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    assert failed["formula_verdict"] == "FAIL"
    assert failed["diff_data"]["fee_diffs"][0]["reason"] == "RATE_ERROR"
    lines[0].fee_items["Commission"] = Decimal("10.014")
    precise = ReconciliationEngine().run(base_request.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    assert precise["diff_data"]["fee_diffs"][0]["formula_pass"] is False


def test_quantity_defaults_and_invalid_values_have_row_numbers():
    mapping = {"fields": {"order_id": "Order", "sku": "SKU", "settled_at": "Settled", "currency": "Currency", "gross_revenue": "Gross", "quantity": "Quantity"},
        "fee_columns": {"Commission": "Commission"}}
    raw = MULTI_FIXTURE.read_bytes()
    parser = TikTokSettlementParser()
    assert parser.parse(raw, mapping)[0][0].quantity == 3
    assert SettlementLine.model_validate(parser.parse(raw, mapping)[0][0].model_dump(exclude={"quantity"})).quantity == 1
    for invalid in (b"0", b"-1", b"1.5", b""):
        with pytest.raises(SettlementParseError, match="第 2 行"):
            parser.parse(raw.replace(b",3,9.00", b"," + invalid + b",9.00"), mapping)


def test_multi_unit_fees_and_sales_are_per_unit(base_request):
    forecast = base_request.model_copy(deep=True)
    forecast.activity.discount_type = "none"
    forecast.activity.extra_commission_rate = Decimal("0")
    forecast.activity.creator_commission_rate = Decimal("0")
    forecast.platform_config.platform_commission_rate = Decimal("0.10")
    forecast.platform_config.creator_commission_rate = Decimal("0")
    forecast.platform_config.payment_fee_rate = Decimal("0")
    forecast.platform_config.fx_loss_rate = Decimal("0")
    forecast.platform_config.tariff_rate = Decimal("0")
    forecast.platform_config.shipping_cost = Decimal("0")
    forecast.platform_config.return_rate = Decimal("0")
    forecast.platform_config.other_variable_cost = Decimal("0")
    mapping = {"fields": {"order_id": "Order", "sku": "SKU", "settled_at": "Settled", "currency": "Currency", "gross_revenue": "Gross", "quantity": "Quantity"},
        "fee_columns": {"Commission": "Commission"}}
    lines, unknown = TikTokSettlementParser().parse(MULTI_FIXTURE.read_bytes(), mapping)
    assert unknown == []
    result = ReconciliationEngine().run(forecast.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    assert result["formula_verdict"] == "PASS"
    assert Decimal(result["diff_data"]["fee_diffs"][0]["absolute_diff"]) <= Decimal("0.01")
    assert result["diff_data"]["fee_diffs"][0]["predicted"] == "9.00"
    assert result["forecast_diff"]["actual_sales"] == 3
    assert result["forecast_diff"]["returned_units"] == 0
    lines[0].refund_amount = Decimal("30")
    refunded = ReconciliationEngine().run(forecast.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    assert refunded["forecast_diff"]["returned_units"] == 3
    assert refunded["forecast_diff"]["actual_return_rate"] == "1.0000"

    single_csv = b"Order,SKU,Settled,Currency,Gross,Commission\no-1,PB-001,2026-09-03,USD,30.00,3.00\n"
    single_mapping = {"fields": {key: value for key, value in mapping["fields"].items() if key != "quantity"}, "fee_columns": mapping["fee_columns"]}
    single_lines, _ = TikTokSettlementParser().parse(single_csv, single_mapping)
    single = ReconciliationEngine().run(forecast.model_dump(mode="json"), single_lines, {"Commission": "平台佣金"})
    assert single["formula_verdict"] == "PASS"
    assert single["forecast_diff"]["actual_sales"] == 1
    assert single["diff_data"]["fee_diffs"][0]["predicted"] == "3.00"
    lines[0].refund_amount = Decimal("0")
    lines[0].gross_revenue = Decimal("100.00")
    lines[0].fee_items["Commission"] = Decimal("10.00")
    rounded = ReconciliationEngine().run(forecast.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    assert rounded["formula_verdict"] == "PASS"
    assert rounded["diff_data"]["fee_diffs"][0]["reason"] == "ROUNDING"
    assert rounded["diff_data"]["fee_diffs"][0]["revenue_rounding_residual"] == "0.01"

    lines[0].gross_revenue = Decimal("10.04")
    lines[0].fee_items["Commission"] = Decimal("1.00")
    rounded_failure = ReconciliationEngine().run(forecast.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    fee_diff = rounded_failure["diff_data"]["fee_diffs"][0]
    assert fee_diff["predicted"] == "1.02"
    assert fee_diff["actual"] == "1.00"
    assert fee_diff["revenue_rounding_residual"] == "-0.01"
    assert fee_diff["reason"] == "RATE_ERROR"
    assert fee_diff["formula_pass"] is False
    assert rounded_failure["formula_verdict"] == "FAIL"

    lines[0].quantity = 4
    lines[0].gross_revenue = Decimal("40.00")
    lines[0].fee_items["Commission"] = Decimal("4.00")
    lines[0].subsidy_amount = Decimal("0.02")
    subsidy_failure = ReconciliationEngine().run(forecast.model_dump(mode="json"), lines, {"Commission": "平台佣金"})
    subsidy_diff = next(row for row in subsidy_failure["diff_data"]["fee_diffs"] if row["fee_item"] == "平台及物流补贴")
    assert subsidy_diff["subsidy_rounding_residual"] == "-0.02"
    assert subsidy_diff["formula_pass"] is False
    assert subsidy_failure["formula_verdict"] == "FAIL"
