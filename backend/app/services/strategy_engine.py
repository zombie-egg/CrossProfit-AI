from __future__ import annotations

from decimal import Decimal

from ..schemas.domain import ProfitAnalysisRequest, ProfitResult, ScenarioResult
from .llm import get_llm_provider
from .profit_engine import ProfitEngine


class StrategyEngine:
    def __init__(self):
        self.llm = get_llm_provider()

    def generate(self, request: ProfitAnalysisRequest, result: ProfitResult, scenarios: list[ScenarioResult]) -> list[str]:
        tips: list[str] = []
        currency = request.activity.currency
        if result.unit_profit <= 0 and result.break_even_price:
            tips.append(f"建议活动售价至少提高至 {currency} {result.break_even_price}；负单件利润不会因销量增加而改善。")
        shipping = next((x.amount for x in result.breakdown if x.item == "物流成本"), Decimal("0"))
        if result.selling_price and shipping / result.selling_price > Decimal("0.18"):
            gains = [shipping * x for x in (Decimal("0.05"), Decimal("0.10"), Decimal("0.15"))]
            tips.append(f"物流占售价 {(shipping / result.selling_price):.1%}，若降低 5%/10%/15%，单件利润约增加 {gains[0]:.2f}/{gains[1]:.2f}/{gains[2]:.2f} {currency}。")
        creator_rate = request.activity.creator_commission_rate
        if creator_rate is None:
            creator_rate = request.platform_config.creator_commission_rate
        creator_cost = result.selling_price * creator_rate
        if creator_cost > 0:
            profit_without_creator = result.unit_profit + creator_cost
            max_rate = max(Decimal("0"), profit_without_creator / result.selling_price) if result.selling_price else Decimal("0")
            if creator_rate > max_rate or result.profit_margin < Decimal("0.10"):
                tips.append(f"当前达人佣金率 {creator_rate:.1%} 压缩利润；保本上限约 {max_rate:.1%}，建议协商阶梯佣金。")
        if request.activity.discount_value > Decimal("0.20") and request.activity.extra_commission_rate + creator_rate > Decimal("0.12"):
            tips.append("折扣、活动额外佣金与达人佣金叠加明显，建议关闭额外优惠叠加或设置最低成交价。")
        pessimistic = next((s for s in scenarios if s.name == "悲观"), None)
        if pessimistic and not pessimistic.profitable:
            tips.append("活动在悲观情景下转为亏损，对退货与物流波动敏感；建议先限量测试并设置止损线。")
        if not tips:
            tips.append("当前利润安全边际较好，可小规模验证转化率后逐步扩大活动量。")
        facts = {
            "unit_profit": str(result.unit_profit), "profit_margin": str(result.profit_margin),
            "break_even_price": str(result.break_even_price),
            "cost_breakdown": {x.item: str(x.amount) for x in result.breakdown},
            "sensitivity": [{"name": x.name, "total_profit": str(x.total_profit)} for x in scenarios],
        }
        try:
            return self.llm.enhance_recommendations(facts, tips)
        except Exception:
            return tips

    def compare(self, named_results: list[tuple[str, ProfitResult]]) -> list[str]:
        if not named_results:
            return []
        best_margin = max(named_results, key=lambda x: x[1].profit_margin)
        best_total = max(named_results, key=lambda x: x[1].estimated_total_profit)
        lowest_risk = max(named_results, key=lambda x: x[1].unit_profit)
        return [f"利润率最高：{best_margin[0]}（{best_margin[1].profit_margin:.1%}）", f"预计总利润最高：{best_total[0]}（{best_total[1].estimated_total_profit}）", f"单件安全边际最高：{lowest_risk[0]}（{lowest_risk[1].unit_profit}/单）"]
