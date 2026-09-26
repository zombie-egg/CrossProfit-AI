from decimal import Decimal

from backend.app.schemas.domain import PortfolioItemInput, PortfolioRequest
from backend.app.services.portfolio_engine import analyze_portfolio
from backend.app.services.profit_engine import ProfitEngine


def test_portfolio_charges_fixed_cost_once(base_request):
    base_request.activity.registration_fee = Decimal("100")
    base_request.activity.ad_budget = Decimal("200")
    base_request.activity.creative_cost = Decimal("50")
    base_request.activity.creator_fixed_fee = Decimal("25")
    base_request.activity.estimated_sales = 10
    first = base_request.product
    second = first.model_copy(update={"sku": "PB-002"})
    payload = PortfolioRequest(activity=base_request.activity, items=[
        PortfolioItemInput(product_id=1, platform_config=base_request.platform_config, estimated_sales=10),
        PortfolioItemInput(product_id=2, platform_config=base_request.platform_config, estimated_sales=10),
    ])
    result = analyze_portfolio(payload, {1: first, 2: second})
    single = ProfitEngine().calculate(base_request)
    expected = single.unit_profit * 20 - Decimal("375")
    assert Decimal(result["total_profit"]) == expected
    assert Decimal(result["fixed_cost"]) == Decimal("375")


def _simple_portfolio(base_request, costs: list[Decimal]) -> dict:
    activity = base_request.activity.model_copy(deep=True)
    activity.discount_type = "none"
    activity.extra_commission_rate = Decimal("0")
    activity.creator_commission_rate = Decimal("0")
    activity.ad_budget = Decimal("20")
    config = base_request.platform_config.model_copy(deep=True)
    config.original_price = Decimal("100")
    config.shipping_cost = Decimal("0")
    config.platform_commission_rate = Decimal("0")
    config.creator_commission_rate = Decimal("0")
    config.payment_fee_rate = Decimal("0")
    config.fx_loss_rate = Decimal("0")
    config.tariff_rate = Decimal("0")
    config.return_rate = Decimal("0")
    config.other_variable_cost = Decimal("0")
    products = {index: base_request.product.model_copy(update={"sku": f"SKU-{index}", "purchase_cost": cost, "packaging_cost": Decimal("0")})
        for index, cost in enumerate(costs, start=1)}
    payload = PortfolioRequest(activity=activity, items=[PortfolioItemInput(product_id=index, platform_config=config, estimated_sales=1)
        for index in products])
    return analyze_portfolio(payload, products)


def test_healthy_skus_have_no_exclusion_candidates(base_request):
    result = _simple_portfolio(base_request, [Decimal("10"), Decimal("20"), Decimal("30")])
    assert Decimal(result["total_profit"]) > 0
    assert result["exclude_candidates"] == []


def test_only_negative_contribution_improves_total_if_removed(base_request):
    result = _simple_portfolio(base_request, [Decimal("10"), Decimal("150")])
    assert len(result["exclude_candidates"]) == 1
    candidate = result["exclude_candidates"][0]
    assert candidate["sku"] == "SKU-2"
    assert candidate["reason"] == "REMOVAL_IMPROVES_TOTAL"
    assert Decimal(candidate["improvement"]) > 0
    assert Decimal(candidate["profit_if_removed"]) - Decimal(result["total_profit"]) == Decimal(candidate["improvement"])
    assert Decimal(candidate["profit_if_removed"]) == Decimal("70")  # 90 contribution - 20 shared fixed cost


def test_single_sku_and_zero_contribution_have_no_exclusion(base_request):
    assert _simple_portfolio(base_request, [Decimal("150")])["exclude_candidates"] == []
    result = _simple_portfolio(base_request, [Decimal("10"), Decimal("100")])
    assert result["exclude_candidates"] == []
    assert result["sku_results"][1]["contribution_flag"] == "NEGATIVE_CONTRIBUTION"
