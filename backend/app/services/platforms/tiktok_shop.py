from decimal import Decimal

from .base import PlatformAdapter


class TikTokShopAdapter(PlatformAdapter):
    name = "tiktok_shop"

    def get_default_fee_rules(self):
        return {
            "platform_commission_rate": Decimal("0.06"),
            "creator_commission_rate": Decimal("0.10"),
            "payment_fee_rate": Decimal("0.029"),
            "return_rate": Decimal("0.08"),
            "demo_default": True,
            "disclaimer": "DEMO DEFAULT：非官方实时费率，请按实际店铺协议修改。",
        }

