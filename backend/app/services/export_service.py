from __future__ import annotations

from io import BytesIO

import pandas as pd

from ..schemas.domain import ProfitAnalysisRequest, ProfitResult, ScenarioResult


class ExportService:
    def summary_frame(self, request: ProfitAnalysisRequest, result: ProfitResult) -> pd.DataFrame:
        return pd.DataFrame([{
            "商品": request.product.name, "SKU": request.product.sku, "平台": request.activity.platform, "活动": request.activity.activity_name,
            "活动价": float(result.selling_price), "总成本": float(result.total_cost), "单件利润": float(result.unit_profit),
            "利润率": float(result.profit_margin), "预计销量": result.estimated_sales, "预计总利润": float(result.estimated_total_profit),
            "盈亏平衡价": float(result.break_even_price) if result.break_even_price else None, "风险等级": result.risk_label,
        }])

    def to_csv(self, request: ProfitAnalysisRequest, result: ProfitResult) -> bytes:
        return self.summary_frame(request, result).to_csv(index=False).encode("utf-8-sig")

    def to_xlsx(self, request: ProfitAnalysisRequest, result: ProfitResult, scenarios: list[ScenarioResult], recommendations: list[str]) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            self.summary_frame(request, result).to_excel(writer, sheet_name="Summary", index=False)
            pd.DataFrame([x.model_dump(mode="json") for x in result.breakdown]).to_excel(writer, sheet_name="Cost Breakdown", index=False)
            pd.DataFrame([x.model_dump(mode="json") for x in scenarios]).to_excel(writer, sheet_name="Scenario Analysis", index=False)
            pd.DataFrame({"Recommendations": recommendations}).to_excel(writer, sheet_name="Recommendations", index=False)
        return output.getvalue()

