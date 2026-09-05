from decimal import Decimal

from .base import PlatformAdapter


class AmazonAdapter(PlatformAdapter):
    name = "amazon"

    def get_default_fee_rules(self):
        return {
            "platform_commission_rate": Decimal("0.15"),
            "creator_commission_rate": Decimal("0"),
            "payment_fee_rate": Decimal("0"),
            "return_rate": Decimal("0.06"),
            "demo_default": True,
            "disclaimer": "DEMO DEFAULT：非官方实时费率，请按站点和类目修改。",
        }

