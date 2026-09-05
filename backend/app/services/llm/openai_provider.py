from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract(self, text: str) -> dict[str, Any]:
        prompt = """从活动规则中提取已明确出现的字段并返回 JSON。不得猜测费率或金额。比例用 0-1 小数。可用字段：platform,activity_name,start_date,end_date,discount_type,discount_value,extra_commission_rate,creator_commission_rate,shipping_subsidy,platform_subsidy,estimated_sales,currency。只返回 JSON。\n"""
        response = self.client.responses.create(model=self.model, input=prompt + text[:12000])
        return json.loads(response.output_text)

    def enhance_recommendations(self, facts: dict[str, Any], recommendations: list[str]) -> list[str]:
        # The deterministic rule recommendations remain authoritative; LLM failure never blocks analysis.
        return recommendations

