from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Product, ProductPlatformConfig, PromotionActivity


PRODUCTS = [
    dict(name="Portable Blender", sku="PB-001", purchase_cost=Decimal("8"), packaging_cost=Decimal("0.8"), weight_kg=Decimal("0.65")),
    dict(name="Phone Stand", sku="PS-002", purchase_cost=Decimal("2.2"), packaging_cost=Decimal("0.3"), weight_kg=Decimal("0.18")),
    dict(name="Mini Projector", sku="MP-003", purchase_cost=Decimal("42"), packaging_cost=Decimal("2.5"), weight_kg=Decimal("1.4")),
]


def seed_demo_data(session: Session) -> None:
    if session.scalar(select(Product.id).limit(1)):
        return
    created: dict[str, Product] = {}
    for item in PRODUCTS:
        product = Product(**item, currency="USD")
        session.add(product)
        session.flush()
        created[item["sku"]] = product
    pb = created["PB-001"]
    configs = [
        ProductPlatformConfig(product_id=pb.id, platform="tiktok_shop", original_price=Decimal("29.99"), shipping_cost=Decimal("4.5"), platform_commission_rate=Decimal("0.06"), creator_commission_rate=Decimal("0.10"), payment_fee_rate=Decimal("0.029"), fx_loss_rate=Decimal("0.015"), tariff_rate=Decimal("0.05"), return_rate=Decimal("0.08"), return_shipping_nonrecoverable=Decimal("2"), other_variable_cost=Decimal("0.35")),
        ProductPlatformConfig(product_id=pb.id, platform="amazon", original_price=Decimal("29.99"), shipping_cost=Decimal("5.5"), platform_commission_rate=Decimal("0.15"), creator_commission_rate=Decimal("0"), payment_fee_rate=Decimal("0"), fx_loss_rate=Decimal("0.01"), tariff_rate=Decimal("0.05"), return_rate=Decimal("0.06"), return_shipping_nonrecoverable=Decimal("2.5"), other_variable_cost=Decimal("0.35")),
    ]
    for sku, tiktok_price, amazon_price, ship in [("PS-002", "15.99", "17.99", "3.1"), ("MP-003", "89.99", "99.99", "8.5")]:
        prod = created[sku]
        configs.extend([
            ProductPlatformConfig(product_id=prod.id, platform="tiktok_shop", original_price=Decimal(tiktok_price), shipping_cost=Decimal(ship), platform_commission_rate=Decimal("0.06"), creator_commission_rate=Decimal("0.10"), payment_fee_rate=Decimal("0.029"), fx_loss_rate=Decimal("0.015"), tariff_rate=Decimal("0.05"), return_rate=Decimal("0.08")),
            ProductPlatformConfig(product_id=prod.id, platform="amazon", original_price=Decimal(amazon_price), shipping_cost=Decimal(ship) + Decimal("1"), platform_commission_rate=Decimal("0.15"), creator_commission_rate=Decimal("0"), payment_fee_rate=Decimal("0"), fx_loss_rate=Decimal("0.01"), tariff_rate=Decimal("0.05"), return_rate=Decimal("0.06")),
        ])
    session.add_all(configs)
    session.flush()
    activities = [
        PromotionActivity(product_id=pb.id, platform="tiktok_shop", activity_name="TikTok Summer Mega Sale", discount_type="percentage", discount_value=Decimal("0.25"), estimated_sales=500, currency="USD", parse_confidence=Decimal("0.95"), missing_fields=[], raw_text="25% discount; seller coupon 0.50; extra commission 3%; creator commission 12%", parameters={"extra_commission_rate": "0.03", "creator_commission_rate": "0.12", "coupon_amount": "0.50"}),
        PromotionActivity(product_id=pb.id, platform="amazon", activity_name="Amazon Prime Promotion", discount_type="percentage", discount_value=Decimal("0.10"), estimated_sales=350, currency="USD", parse_confidence=Decimal("0.96"), missing_fields=[], raw_text="Prime promotion: 10% discount", parameters={"extra_commission_rate": "0.01", "creator_commission_rate": "0", "platform_subsidy": "0.30"}),
        PromotionActivity(product_id=pb.id, platform="tiktok_shop", activity_name="TikTok Creator Flash Sale", discount_type="percentage", discount_value=Decimal("0.30"), estimated_sales=800, currency="USD", parse_confidence=Decimal("0.93"), missing_fields=[], raw_text="30% discount; creator commission 20%; extra commission 4%", parameters={"extra_commission_rate": "0.04", "creator_commission_rate": "0.20", "ad_budget": "300"}),
    ]
    session.add_all(activities)
    session.commit()
