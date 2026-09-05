from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapedPage, ScraperError


class GenericScraper(BaseScraper):
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    @staticmethod
    def validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ScraperError("仅支持公开的 HTTP/HTTPS 活动链接")
        host = parsed.hostname.lower()
        if host == "localhost" or host.endswith(".local"):
            raise ScraperError("出于安全考虑，不能访问本机或内网地址")
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443)}
        except socket.gaierror as exc:
            raise ScraperError("无法解析活动链接域名") from exc
        for value in addresses:
            ip = ipaddress.ip_address(value)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise ScraperError("出于安全考虑，不能访问本机或内网地址")

    def fetch(self, url: str) -> ScrapedPage:
        self.validate_url(url)
        headers = {"User-Agent": "Mozilla/5.0 CrossProfitAI/1.0 (+promotion-analysis)"}
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False, headers=headers) as client:
                response = client.get(url)
                if 300 <= response.status_code < 400:
                    raise ScraperError("页面发生重定向，请粘贴最终公开链接或活动规则文本")
                response.raise_for_status()
                if "text/html" not in response.headers.get("content-type", "text/html"):
                    raise ScraperError("链接不是可解析的网页")
        except (httpx.HTTPError, ScraperError) as exc:
            if isinstance(exc, ScraperError):
                raise
            raise ScraperError("平台页面暂时无法自动读取，可能存在登录或访问限制") from exc
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description = soup.find("meta", attrs={"name": "description"})
        meta = description.get("content", "") if description else ""
        text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
        return ScrapedPage(url=url, title=title, text=f"{title}\n{meta}\n{text}"[:100_000])

