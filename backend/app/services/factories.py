from __future__ import annotations

from decimal import Decimal

from ..models import Product, ProductPlatformConfig, PromotionActivity
from ..schemas.domain import PlatformConfigInput, ProductInput, ProfitAnalysisRequest, PromotionActivityInput


def request_from_models(product: Product, config: ProductPlatformConfig, activity: PromotionActivity) -> ProfitAnalysisRequest:
    params = activity.parameters or {}
    return ProfitAnalysisRequest(
        product=ProductInput(name=product.name, sku=product.seller_sku or product.sku, purchase_cost=product.purchase_cost, packaging_cost=product.packaging_cost, weight_kg=product.weight_kg, volume_cm3=product.volume_cm3, currency=product.currency),
        platform_config=PlatformConfigInput(
            platform=config.platform, original_price=config.original_price, shipping_cost=config.shipping_cost,
            platform_commission_rate=config.platform_commission_rate, creator_commission_rate=config.creator_commission_rate,
            payment_fee_rate=config.payment_fee_rate, fx_loss_rate=config.fx_loss_rate, tariff_rate=config.tariff_rate,
            tariff_basis=config.tariff_basis, return_rate=config.return_rate, return_shipping_nonrecoverable=config.return_shipping_nonrecoverable,
            return_product_loss_rate=config.return_product_loss_rate, platform_nonrefundable_fee_rate=config.platform_nonrefundable_fee_rate,
            other_variable_cost=config.other_variable_cost, demo_default=config.demo_default,
        ),
        activity=PromotionActivityInput(
            platform=activity.platform, activity_name=activity.activity_name, activity_type=activity.activity_type, source_url=activity.source_url,
            start_date=activity.start_date, end_date=activity.end_date, discount_type=activity.discount_type, discount_value=activity.discount_value,
            estimated_sales=activity.estimated_sales, currency=activity.currency, raw_text=activity.raw_text, parse_confidence=activity.parse_confidence,
            missing_fields=activity.missing_fields or [], **{k: Decimal(str(v)) for k, v in params.items()},
        ),
    )
