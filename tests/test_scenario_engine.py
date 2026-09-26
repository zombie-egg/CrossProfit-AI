from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.scenario_engine import ScenarioEngine


def test_uncalibrated_scenarios_only_change_cost_inputs(base_request):
    rows = ScenarioEngine().analyze(base_request)
    assert [row.name for row in rows] == ["基准", "物流+10%", "物流-10%", "退货率+20%", "退货率-20%"]
    assert all(row.sales_multiplier == Decimal("1") for row in rows)
    assert [row.source for row in rows] == ["default", "sensitivity", "sensitivity", "sensitivity", "sensitivity"]
    assert all("非销量预测" in row.confidence_note for row in rows)
    base_return = base_request.activity.return_rate_override or base_request.platform_config.return_rate
    assert rows[0].return_rate == base_return
    assert rows[1].shipping_multiplier == Decimal("1.10")
    assert rows[3].return_rate == min(Decimal("1"), base_return * Decimal("1.20"))


def test_calibrated_scenarios_use_measured_quantiles(base_request):
    parameters = {
        "sales_multiplier": SimpleNamespace(p25=Decimal("0.80"), p50=Decimal("1.00"), p75=Decimal("1.25"), sample_size=30, report_count=3),
        "return_rate": SimpleNamespace(p25=Decimal("0.02"), p50=Decimal("0.04"), p75=Decimal("0.09"), sample_size=30, report_count=3),
    }
    rows = ScenarioEngine().analyze(base_request, parameters)
    assert [row.name for row in rows] == ["乐观", "基准", "悲观"]
    assert [row.sales_multiplier for row in rows] == [Decimal("1.25"), Decimal("1.00"), Decimal("0.80")]
    assert [row.return_rate for row in rows] == [Decimal("0.02"), Decimal("0.04"), Decimal("0.09")]
    assert all(row.source == "calibrated" and row.sample_size == 30 for row in rows)


def test_insufficient_calibration_samples_fall_back_to_sensitivity(base_request):
    parameters = {
        "sales_multiplier": SimpleNamespace(sample_size=19, report_count=3),
        "return_rate": SimpleNamespace(sample_size=19, report_count=3),
    }
    rows = ScenarioEngine().analyze(base_request, parameters)
    assert all(row.sales_multiplier == Decimal("1") for row in rows)
    assert rows[0].sample_size == 19
    assert "样本 19 单不足" in rows[0].confidence_note
