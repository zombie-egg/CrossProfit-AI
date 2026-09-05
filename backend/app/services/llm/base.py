from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    def extract(self, text: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def enhance_recommendations(self, facts: dict[str, Any], recommendations: list[str]) -> list[str]:
        raise NotImplementedError

