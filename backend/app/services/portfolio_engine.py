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
            "revenue": str(sku_revenue), "marginal_contribution": str(sku_contribution), "margin": str(result.profit_margin),
            "risk_level": result.risk_level, "contribution_flag": "NEGATIVE_CONTRIBUTION" if sku_contribution <= 0 else None})
    total_profit = money(contribution - fixed)
    weighted_margin = rate(total_profit / revenue) if revenue else Decimal("0")
    excluded = []
    if len(rows) > 1:
        for row in sorted(rows, key=lambda item: Decimal(item["marginal_contribution"])):
            sku_contribution = Decimal(row["marginal_contribution"])
            if sku_contribution > 0:
                continue
            profit_if_removed = money(contribution - sku_contribution - fixed)
            improvement = money(profit_if_removed - total_profit)
            if improvement > 0:
                excluded.append({**row, "reason": "REMOVAL_IMPROVES_TOTAL",
                    "profit_if_removed": str(profit_if_removed), "improvement": str(improvement)})
    return {"total_profit": str(total_profit), "total_revenue": str(money(revenue)), "weighted_margin": str(weighted_margin),
        "fixed_cost": str(money(fixed)), "risk_distribution": dict(risk), "sku_results": rows, "exclude_candidates": excluded}
