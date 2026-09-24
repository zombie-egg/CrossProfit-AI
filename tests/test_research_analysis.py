from __future__ import annotations

import pytest
from pydantic import ValidationError
from types import SimpleNamespace

from backend.app.services.research_analysis import HistoricalMetrics, ResearchRequest, discover_public_sources, research_analysis
from backend.app.services.scraper.base import ScrapedPage


def test_research_keeps_missing_history_explicit(monkeypatch):
    from backend.app.services import research_analysis as module

    monkeypatch.setattr(module, "settings", SimpleNamespace(deepseek_api_key=None))
    monkeypatch.setattr(module.GenericScraper, "fetch", lambda self, url: ScrapedPage(url, "官方规则", "活动规则文本"))
    request = ResearchRequest.model_validate({
        "analysis": {
            "product": {"name": "测试商品", "sku": "TEST", "purchase_cost": "8"},
            "platform_config": {"platform": "tiktok_shop", "original_price": "20"},
            "activity": {"platform": "tiktok_shop", "activity_name": "测试活动", "source_url": "https://example.com/promotion"},
        },
        "historical": {"period": "去年同期", "visitors": 1000, "orders": 50, "returns": 5, "source": "卖家后台导出"},
    })
    report = research_analysis(request)
    assert report["historical"]["conversion_rate"] == 0.05
    assert report["historical"]["return_rate"] == 0.1
    assert report["sources"][0]["url"] == "https://example.com/promotion"
    assert report["provider"] == "rules"


def test_historical_counts_require_same_denominator():
    with pytest.raises(ValidationError):
        HistoricalMetrics(visitors=10, orders=11)
    with pytest.raises(ValidationError):
        HistoricalMetrics(orders=10, returns=11)


def test_public_search_uses_tool_results_not_model_text(monkeypatch):
    from backend.app.services import research_analysis as module

    monkeypatch.setattr(module, "settings", SimpleNamespace(deepseek_api_key="test", deepseek_model="deepseek-flash"))
    monkeypatch.setattr(module.GenericScraper, "validate_url", lambda url: None)

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"content": [
                {"type": "web_search_tool_result", "content": [{"title": "官方商品", "url": "https://example.com/product"}]},
                {"type": "text", "text": "虚构来源 https://made-up.example/"},
            ]}

    monkeypatch.setattr(module.httpx, "post", lambda *args, **kwargs: Response())
    assert discover_public_sources("测试商品", "tiktok_shop") == [{"url": "https://example.com/product", "title": "官方商品"}]
