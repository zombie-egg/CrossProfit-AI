from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.schemas.domain import PricingTarget
from backend.app.services.profit_engine import ProfitEngine


def test_fixed_amount_target_round_trips_through_forward_engine(base_request):
    engine = ProfitEngine()
    without_fixed = engine.target_price(base_request, PricingTarget(mode="fixed_amount", value=Decimal("3.50")))
    base_request.activity.registration_fee = Decimal("50")
    answer = engine.target_price(base_request, PricingTarget(mode="fixed_amount", value=Decimal("3.50")))
    assert answer.reachable and answer.price is not None and answer.result is not None
    assert answer.price == without_fixed.price
    assert answer.result.selling_price == answer.price
    assert abs(answer.result.unit_profit - Decimal("3.50")) <= Decimal("0.01")
    assert answer.result.fixed_cost == Decimal("50.00")
    assert answer.result.break_even_quantity is not None


def test_fixed_margin_target_round_trips_through_forward_engine(base_request):
    answer = ProfitEngine().target_price(base_request, PricingTarget(mode="fixed_margin", value=Decimal("0.25")))
    assert answer.reachable and answer.result is not None
    assert abs(answer.result.profit_margin - Decimal("0.25")) <= Decimal("0.001")


def test_unreachable_variable_rate_and_margin(base_request):
    base_request.platform_config.platform_commission_rate = Decimal("1")
    variable = ProfitEngine().target_price(base_request, PricingTarget(mode="fixed_amount", value=Decimal("1")))
    assert not variable.reachable and variable.price is None and variable.result is None
    assert "100%" in variable.reason

    base_request.platform_config.platform_commission_rate = Decimal("0.70")
    margin = ProfitEngine().target_price(base_request, PricingTarget(mode="fixed_margin", value=Decimal("0.30")))
    assert not margin.reachable and margin.price is None and margin.result is None
    assert "目标利润率" in margin.reason


def test_zero_target_equals_existing_break_even_price(base_request):
    engine = ProfitEngine()
    answer = engine.target_price(base_request, PricingTarget(mode="fixed_amount", value=Decimal("0")))
    assert answer.price == engine.break_even_price(base_request)


@pytest.mark.parametrize("value", ["-0.01", "1", "1.1"])
def test_margin_target_rejects_out_of_range(value):
    with pytest.raises(ValidationError):
        PricingTarget(mode="fixed_margin", value=Decimal(value))
