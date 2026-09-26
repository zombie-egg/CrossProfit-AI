from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.scenario_engine import ScenarioEngine
from backend.app.services.calibration import percentile


def test_small_sample_keeps_default_scenarios_and_warns(base_request):
    small = SimpleNamespace(p25=Decimal("0.01"), p50=Decimal("0.02"), p75=Decimal("0.03"), sample_size=8, report_count=2)
    scenarios = ScenarioEngine().analyze(base_request, {"return_rate": small, "sales_multiplier": small})
    assert all(row.source == "default" and row.sample_size == 8 for row in scenarios)
    assert all(row.confidence_note == "样本 8 单，区间不可信" for row in scenarios)
    assert scenarios[0].sales_multiplier == Decimal("1.20")


def test_calibrated_quantiles_used_after_threshold(base_request):
    returns = SimpleNamespace(p25=Decimal("0.02"), p50=Decimal("0.04"), p75=Decimal("0.09"), sample_size=50, report_count=3)
    sales = SimpleNamespace(p25=Decimal("0.70"), p50=Decimal("0.95"), p75=Decimal("1.30"), sample_size=50, report_count=3)
    scenarios = ScenarioEngine().analyze(base_request, {"return_rate": returns, "sales_multiplier": sales})
    assert [row.sales_multiplier for row in scenarios] == [Decimal("1.30"), Decimal("0.95"), Decimal("0.70")]
    assert [row.return_rate for row in scenarios] == [Decimal("0.02"), Decimal("0.04"), Decimal("0.09")]
    assert all(row.source == "calibrated" and row.confidence_note is None for row in scenarios)
    assert percentile([Decimal("1"), Decimal("2"), Decimal("3")], Decimal("0.5")) == Decimal("2.0000")
