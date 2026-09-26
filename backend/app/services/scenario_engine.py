from __future__ import annotations

from decimal import Decimal

from ..schemas.domain import ProfitAnalysisRequest, ScenarioResult
from .calibration import MIN_ORDERS, MIN_REPORTS
from .profit_engine import ProfitEngine


class ScenarioEngine:
    definitions = (
        ("乐观", Decimal("1.20"), Decimal("-0.03"), Decimal("0.95")),
        ("基准", Decimal("1.00"), Decimal("0"), Decimal("1.00")),
        ("悲观", Decimal("0.80"), Decimal("0.05"), Decimal("1.10")),
    )

    def __init__(self, profit_engine: ProfitEngine | None = None):
        self.profit_engine = profit_engine or ProfitEngine()

    def analyze(self, request: ProfitAnalysisRequest, parameters: dict | None = None) -> list[ScenarioResult]:
        output: list[ScenarioResult] = []
        parameters = parameters or {}
        sales = parameters.get("sales_multiplier")
        returns = parameters.get("return_rate")
        sample_size = min((row.sample_size for row in parameters.values()), default=0)
        calibrated = bool(sales and returns and sample_size >= MIN_ORDERS and sales.report_count >= MIN_REPORTS and returns.report_count >= MIN_REPORTS)
        note = None if calibrated else f"样本 {sample_size} 单，区间不可信"
        base_return = request.activity.return_rate_override
        if base_return is None:
            base_return = request.platform_config.return_rate
        for index, (name, default_sales, return_delta, shipping_mult) in enumerate(self.definitions):
            sales_mult = (sales.p75, sales.p50, sales.p25)[index] if calibrated else default_sales
            scenario_return = (returns.p25, returns.p50, returns.p75)[index] if calibrated else max(Decimal("0"), min(Decimal("1"), base_return + return_delta))
            changed = request.model_copy(deep=True)
            changed.activity.estimated_sales = max(0, int(request.activity.estimated_sales * sales_mult))
            changed.activity.return_rate_override = scenario_return
            base_shipping = request.activity.seller_shipping_cost
            if base_shipping is None:
                base_shipping = request.platform_config.shipping_cost
            changed.activity.seller_shipping_cost = base_shipping * shipping_mult
            result = self.profit_engine.calculate(changed)
            output.append(ScenarioResult(name=name, sales_multiplier=sales_mult, return_rate=changed.activity.return_rate_override, shipping_multiplier=shipping_mult, unit_profit=result.unit_profit, profit_margin=result.profit_margin, total_profit=result.estimated_total_profit, profitable=result.estimated_total_profit > 0, sample_size=sample_size, source="calibrated" if calibrated else "default", confidence_note=note))
        return output
