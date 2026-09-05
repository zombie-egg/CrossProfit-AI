from __future__ import annotations

from abc import ABC
from decimal import Decimal

from ...schemas.domain import PlatformConfigInput, PromotionActivityInput


class PlatformAdapter(ABC):
    name = "generic"

    def get_default_fee_rules(self) -> dict[str, Decimal | str | bool]:
        return {
            "platform_commission_rate": Decimal("0.10"),
            "payment_fee_rate": Decimal("0.03"),
            "demo_default": True,
            "disclaimer": "DEMO DEFAULT：请按站点、类目与卖家协议覆盖。",
        }

    def normalize_activity(self, activity: PromotionActivityInput) -> PromotionActivityInput:
        activity.platform = self.name
        return activity

    def validate_activity(self, activity: PromotionActivityInput) -> list[str]:
        errors: list[str] = []
        if activity.discount_type == "percentage" and not Decimal("0") <= activity.discount_value < Decimal("1"):
            errors.append("百分比折扣必须在 0 到 1 之间")
        return errors

    def calculate_platform_specific_costs(self, selling_price: Decimal, config: PlatformConfigInput) -> Decimal:
        return Decimal("0")

