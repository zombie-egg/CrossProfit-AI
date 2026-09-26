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
