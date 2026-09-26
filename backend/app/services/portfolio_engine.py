from __future__ import annotations

from collections import Counter
from decimal import Decimal

from ..schemas.domain import PortfolioRequest, ProductInput, ProfitAnalysisRequest
from .profit_engine import ProfitEngine, money, rate


def analyze_portfolio(payload: PortfolioRequest, products: dict[int, ProductInput]) -> dict:
    engine = ProfitEngine()
    rows = []
    revenue = Decimal("0")
    contribution = Decimal("0")
    risk = Counter()
    fixed = payload.activity.fixed_cost
    for item in payload.items:
        activity = payload.activity.model_copy(deep=True)
        activity.estimated_sales = item.estimated_sales
        activity.registration_fee = Decimal("0")
        activity.ad_budget = Decimal("0")
        activity.creative_cost = Decimal("0")
        activity.creator_fixed_fee = Decimal("0")
        result = engine.calculate(ProfitAnalysisRequest(product=products[item.product_id], platform_config=item.platform_config, activity=activity))
        sku_revenue = result.estimated_revenue
        sku_contribution = result.estimated_total_profit
        revenue += sku_revenue
        contribution += sku_contribution
        risk[result.risk_level] += 1
        rows.append({"product_id": item.product_id, "sku": products[item.product_id].sku, "estimated_sales": item.estimated_sales,
            "revenue": str(sku_revenue), "marginal_contribution": str(sku_contribution), "margin": str(result.profit_margin), "risk_level": result.risk_level})
    total_profit = money(contribution - fixed)
    weighted_margin = rate(total_profit / revenue) if revenue else Decimal("0")
    excluded = [{**row, "reason": "NEGATIVE_CONTRIBUTION" if Decimal(row["marginal_contribution"]) <= 0 else "DILUTES_MARGIN"}
        for row in sorted(rows, key=lambda row: Decimal(row["marginal_contribution"]))
        if Decimal(row["marginal_contribution"]) <= 0 or (Decimal(row["margin"]) < weighted_margin and len(rows) > 1)]
    return {"total_profit": str(total_profit), "total_revenue": str(money(revenue)), "weighted_margin": str(weighted_margin),
        "fixed_cost": str(money(fixed)), "risk_distribution": dict(risk), "sku_results": rows, "exclude_candidates": excluded}
