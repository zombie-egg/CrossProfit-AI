from __future__ import annotations

from decimal import Decimal

from .base import SettlementLine

ENGINE_ITEMS = frozenset(("平台佣金", "活动额外佣金", "达人佣金", "采购成本", "包装成本", "物流成本", "关税", "支付手续费", "汇率损耗", "退货风险准备金", "其他可变费用", "卖家优惠券", "平台及物流补贴"))


def normalize_fees(line: SettlementLine, mapping: dict[str, str]) -> tuple[dict[str, Decimal], list[dict]]:
    normalized: dict[str, Decimal] = {}
    unmapped: list[dict] = []
    for raw_name, value in line.fee_items.items():
        name = mapping.get(raw_name, raw_name if raw_name in ENGINE_ITEMS else None)
        if name not in ENGINE_ITEMS:
            unmapped.append({"order_id": line.order_id, "sku": line.sku, "fee_name": raw_name, "amount": str(value)})
        else:
            normalized[name] = normalized.get(name, Decimal("0")) + value
    return normalized, unmapped
