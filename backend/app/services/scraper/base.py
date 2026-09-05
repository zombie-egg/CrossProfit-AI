from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ScraperError(Exception):
    pass


@dataclass
class ScrapedPage:
    url: str
    title: str
    text: str


class BaseScraper(ABC):
    @abstractmethod
    def fetch(self, url: str) -> ScrapedPage:
        raise NotImplementedError

