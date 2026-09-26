from .base import SettlementParser


class AmazonSettlementParser(SettlementParser):
    @property
    def platform(self) -> str:
        return "amazon"
