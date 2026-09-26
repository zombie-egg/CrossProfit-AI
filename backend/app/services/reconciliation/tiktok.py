from .base import SettlementParser


class TikTokSettlementParser(SettlementParser):
    @property
    def platform(self) -> str:
        return "tiktok_shop"
