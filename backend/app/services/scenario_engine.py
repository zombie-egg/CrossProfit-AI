from __future__ import annotations

from decimal import Decimal

from ..schemas.domain import ProfitAnalysisRequest, ScenarioResult
from .profit_engine import ProfitEngine


class ScenarioEngine:
    definitions = (
        ("乐观", Decimal("1.20"), Decimal("-0.03"), Decimal("0.95")),
        ("基准", Decimal("1.00"), Decimal("0"), Decimal("1.00")),
        ("悲观", Decimal("0.80"), Decimal("0.05"), Decimal("1.10")),
    )

    def __init__(self, profit_engine: ProfitEngine | None = None):
        self.profit_engine = profit_engine or ProfitEngine()

    def analyze(self, request: ProfitAnalysisRequest) -> list[ScenarioResult]:
        output: list[ScenarioResult] = []
        base_return = request.activity.return_rate_override
        if base_return is None:
            base_return = request.platform_config.return_rate
        for name, sales_mult, return_delta, shipping_mult in self.definitions:
            changed = request.model_copy(deep=True)
            changed.activity.estimated_sales = max(0, int(request.activity.estimated_sales * sales_mult))
            changed.activity.return_rate_override = max(Decimal("0"), min(Decimal("1"), base_return + return_delta))
            base_shipping = request.activity.seller_shipping_cost
            if base_shipping is None:
                base_shipping = request.platform_config.shipping_cost
            changed.activity.seller_shipping_cost = base_shipping * shipping_mult
            result = self.profit_engine.calculate(changed)
            output.append(ScenarioResult(name=name, sales_multiplier=sales_mult, return_rate=changed.activity.return_rate_override, shipping_multiplier=shipping_mult, unit_profit=result.unit_profit, profit_margin=result.profit_margin, total_profit=result.estimated_total_profit, profitable=result.estimated_total_profit > 0))
        return output

