from typing import Any

from .base import LLMProvider


class MockProvider(LLMProvider):
    mode_label = "规则分析模式"

    def extract(self, text: str) -> dict[str, Any]:
        return {}

    def enhance_recommendations(self, facts: dict[str, Any], recommendations: list[str]) -> list[str]:
        return recommendations

