from backend.app.services.scenario_engine import ScenarioEngine


def test_three_scenarios_and_pessimistic_is_worse(base_request):
    rows = ScenarioEngine().analyze(base_request)
    assert [x.name for x in rows] == ["乐观", "基准", "悲观"]
    assert rows[0].unit_profit > rows[2].unit_profit

