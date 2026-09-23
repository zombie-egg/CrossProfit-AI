from ...config import settings
from .base import LLMProvider
from .mock_provider import MockProvider


def get_llm_provider() -> LLMProvider:
    if settings.deepseek_api_key:
        try:
            from .deepseek_provider import DeepSeekProvider
            return DeepSeekProvider(settings.deepseek_api_key, settings.deepseek_model)
        except Exception:
            pass
    if settings.openai_api_key:
        try:
            from .openai_provider import OpenAIProvider
            return OpenAIProvider(settings.openai_api_key, settings.openai_model)
        except Exception:
            pass
    return MockProvider()


def llm_status() -> dict[str, str | bool]:
    if settings.deepseek_api_key:
        return {"provider": "deepseek", "model": settings.deepseek_model, "configured": True}
    if settings.openai_api_key:
        return {"provider": "openai", "model": settings.openai_model, "configured": True}
    return {"provider": "rules", "model": "", "configured": False}
