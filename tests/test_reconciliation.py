from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.services.reconciliation.base import SettlementParseError
from backend.app.services.reconciliation.tiktok import TikTokSettlementParser
from backend.app.services.reconciliation.amazon import AmazonSettlementParser
from backend.app.services.reconciliation.mapper import normalize_fees
from backend.app.services.reconciliation.engine import ReconciliationEngine


FIXTURE = Path(__file__).parent / "fixtures" / "settlement_sample.csv"
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
