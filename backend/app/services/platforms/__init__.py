from .amazon import AmazonAdapter
from .base import PlatformAdapter
from .shein import SheinAdapter
from .temu import TemuAdapter
from .tiktok_shop import TikTokShopAdapter

ADAPTERS = {
    "tiktok": TikTokShopAdapter(),
    "tiktok_shop": TikTokShopAdapter(),
    "amazon": AmazonAdapter(),
    "temu": TemuAdapter(),
    "shein": SheinAdapter(),
}


def get_adapter(platform: str) -> PlatformAdapter:
    return ADAPTERS.get(platform.lower().replace(" ", "_"), PlatformAdapter())

