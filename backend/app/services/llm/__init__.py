from ...config import settings
from .base import LLMProvider
from .mock_provider import MockProvider


def get_llm_provider() -> LLMProvider:
    if settings.openai_api_key:
        try:
            from .openai_provider import OpenAIProvider
            return OpenAIProvider(settings.openai_api_key, settings.openai_model)
        except Exception:
            pass
    return MockProvider()

