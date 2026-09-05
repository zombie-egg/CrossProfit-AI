from decimal import Decimal

import pytest

from backend.app.services.profit_engine import ProfitEngine


def test_normal_profit_and_discount(base_request):
    result = ProfitEngine().calculate(base_request)
    assert result.selling_price == Decimal("22.49")
    assert result.discount_amount == Decimal("7.50")
    assert result.unit_profit > 0
    assert result.estimated_total_profit == result.unit_profit * 500


def test_single_unit_loss(base_request):
    base_request.activity.discount_value = Decimal("0.50")
    base_request.activity.creator_commission_rate = Decimal("0.30")
    assert ProfitEngine().calculate(base_request).risk_level == "LOSS"


def test_zero_commission(base_request):
    base_request.platform_config.platform_commission_rate = Decimal("0")
    base_request.activity.extra_commission_rate = Decimal("0")
    base_request.activity.creator_commission_rate = Decimal("0")
    result = ProfitEngine().calculate(base_request)
    assert next(x.amount for x in result.breakdown if x.item == "平台佣金") == 0


def test_high_return_rate_reduces_profit(base_request):
    normal = ProfitEngine().calculate(base_request)
    base_request.activity.return_rate_override = Decimal("0.60")
    assert ProfitEngine().calculate(base_request).unit_profit < normal.unit_profit


def test_creator_commission(base_request):
    result = ProfitEngine().calculate(base_request)
    assert next(x.amount for x in result.breakdown if x.item == "达人佣金") == Decimal("2.70")


@pytest.mark.parametrize("field", ["platform_subsidy", "shipping_subsidy"])
def test_subsidies_increase_profit(base_request, field):
    before = ProfitEngine().calculate(base_request).unit_profit
    setattr(base_request.activity, field, Decimal("1.25"))
    after = ProfitEngine().calculate(base_request).unit_profit
    assert after - before == Decimal("1.25")


def test_tariff_basis_changes_cost(base_request):
    product_basis = ProfitEngine().calculate(base_request)
    base_request.platform_config.tariff_basis = "selling_price"
    sale_basis = ProfitEngine().calculate(base_request)
    assert sale_basis.total_cost > product_basis.total_cost


def test_break_even_price_is_consistent(base_request):
    result = ProfitEngine().calculate(base_request)
    assert result.break_even_price is not None
    changed = base_request.model_copy(deep=True)
    changed.platform_config.original_price = result.break_even_price
    changed.activity.discount_type = "none"
    changed.activity.discount_value = Decimal("0")
    assert abs(ProfitEngine().calculate(changed).unit_profit) <= Decimal("0.01")


def test_break_even_quantity_with_fixed_cost(base_request):
    base_request.activity.ad_budget = Decimal("100")
    result = ProfitEngine().calculate(base_request)
    assert result.break_even_quantity is not None
    assert result.break_even_quantity * result.unit_profit >= Decimal("100")


def test_no_break_even_quantity_without_fixed_cost(base_request):
    assert ProfitEngine().calculate(base_request).break_even_quantity is None


def test_missing_fields_use_config_and_are_marked(base_request):
    base_request.activity.creator_commission_rate = None
    base_request.activity.return_rate_override = None
    result = ProfitEngine().calculate(base_request)
    assert result.assumptions
    assert next(x.amount for x in result.breakdown if x.item == "达人佣金") > 0


def test_currency_rounding(base_request):
    base_request.platform_config.original_price = Decimal("19.999")
    result = ProfitEngine().calculate(base_request)
    assert result.selling_price.as_tuple().exponent == -2
    assert result.unit_profit.as_tuple().exponent == -2

