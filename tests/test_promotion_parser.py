from pathlib import Path
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from backend.app.services.promotion_parser import PromotionParserService
from backend.app.services.scraper.base import ScrapedPage, ScraperError
from backend.app.services.scraper.generic_scraper import GenericScraper


FIXTURES = Path(__file__).parent / "fixtures"


class FixtureScraper:
    def __init__(self, filename): self.filename = filename
    def fetch(self, url):
        html = (FIXTURES / self.filename).read_text()
        soup = BeautifulSoup(html, "html.parser")
        return ScrapedPage(url=url, title=soup.title.text, text=soup.get_text("\n"))


def test_tiktok_fixture_extraction():
    parsed = PromotionParserService(FixtureScraper("tiktok_activity.html")).parse(url="https://example.com")
    assert parsed.activity.platform == "tiktok_shop"
    assert parsed.activity.activity_name == "TikTok Summer Mega Sale"
    assert parsed.activity.discount_value == Decimal("0.25")
    assert parsed.activity.creator_commission_rate == Decimal("0.12")
    assert parsed.activity.estimated_sales == 500
    assert parsed.activity.start_date.isoformat() == "2026-06-01"


def test_amazon_fixture_extraction():
    parsed = PromotionParserService(FixtureScraper("amazon_activity.html")).parse(url="https://example.com")
    assert parsed.activity.platform == "amazon"
    assert parsed.activity.discount_value == Decimal("0.10")
    assert parsed.activity.extra_commission_rate == Decimal("0.01")


def test_fetch_failure_falls_back():
    class Broken:
        def fetch(self, url): raise ScraperError("blocked")
    parsed = PromotionParserService(Broken()).parse(url="https://example.com", raw_text="TikTok Sale discount 20%")
    assert parsed.fetch_warning
    assert parsed.activity.discount_value == Decimal("0.20")


def test_platform_falls_back_to_tiktok_url_when_page_text_has_no_platform():
    class PageOnly:
        def fetch(self, url):
            return ScrapedPage(url=url, title="Summer Deal", text="Summer Deal discount 20%")

    parsed = PromotionParserService(PageOnly()).parse(url="https://shop.tiktok.com/us/pdp/example/123")
    assert parsed.activity.platform == "tiktok_shop"


def test_security_challenge_enters_smart_fallback(monkeypatch):
    class Response:
        status_code = 200
        headers = {"content-type": "text/html"}
        text = "<html><title>Security Check</title><body>Security Check</body></html>"

        def raise_for_status(self):
            return None

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url):
            return Response()

    monkeypatch.setattr(
        "backend.app.services.scraper.generic_scraper.socket.getaddrinfo",
        lambda *args: [(None, None, None, None, ("8.8.8.8", 443))],
    )
    monkeypatch.setattr(
        "backend.app.services.scraper.generic_scraper.httpx.Client",
        lambda **kwargs: Client(),
    )
    parsed = PromotionParserService().parse(url="https://shop.tiktok.com/us/pdp/example/123")
    assert parsed.activity.platform == "tiktok_shop"
    assert parsed.fetch_warning
    assert "访问验证" in parsed.fetch_warning


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/admin", "http://localhost:8000", "ftp://example.com/x"])
def test_ssrf_protection(url):
    with pytest.raises(ScraperError):
        GenericScraper.validate_url(url)
