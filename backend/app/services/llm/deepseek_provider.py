from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from .base import LLMProvider


class DeepSeekProvider(LLMProvider):
    """Optional qualitative analysis; financial values remain engine-owned."""

    def __init__(self, api_key: str, model: str = "deepseek-flash", client: Any | None = None):
        self.client = client or OpenAI(api_key=api_key, base_url="https://api.deepseek.com", timeout=12.0, max_retries=0)
        self.model = model

    def extract(self, text: str) -> dict[str, Any]:
        # Numeric rule extraction is intentionally owned by the deterministic parser.
        # Unverified model values must not silently enter the profit calculation.
        return {}

    def enhance_recommendations(self, facts: dict[str, Any], recommendations: list[str]) -> list[str]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是跨境卖家的经营分析助手。只根据给定的计算结果和已有建议，补充最多两条可执行的定性建议。不得重新计算、修改利润数字、编造平台费率或承诺盈利。不要输出任何数字、百分比、货币金额或公式。只返回 JSON 对象，格式为 {\"suggestions\":[\"建议\"]}。"},
                {"role": "user", "content": json.dumps({"facts": facts, "existing_recommendations": recommendations}, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},
            temperature=0.2,
            max_tokens=240,
        )
        if response.choices[0].finish_reason != "stop":
            return recommendations
        content = response.choices[0].message.content or ""
        data = json.loads(content)
        suggestions = data.get("suggestions", []) if isinstance(data, dict) else []
        if not isinstance(suggestions, list):
            return recommendations
        additions: list[str] = []
        for item in suggestions[:2]:
            if not isinstance(item, str):
                continue
            value = item.strip()
            if not 8 <= len(value) <= 120 or re.search(r"[0-9０-９%％$¥￥]", value):
                continue
            if value not in recommendations and value not in additions:
                additions.append(value)
        return recommendations + additions
