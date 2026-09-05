from decimal import Decimal

import pytest

from backend.app.schemas.domain import PlatformConfigInput, ProductInput, ProfitAnalysisRequest, PromotionActivityInput


@pytest.fixture
def base_request():
    return ProfitAnalysisRequest(
        product=ProductInput(name="Portable Blender", sku="PB-001", purchase_cost=Decimal("8"), packaging_cost=Decimal("0.8")),
        platform_config=PlatformConfigInput(platform="tiktok_shop", original_price=Decimal("29.99"), shipping_cost=Decimal("4.5"), platform_commission_rate=Decimal("0.06"), creator_commission_rate=Decimal("0.10"), payment_fee_rate=Decimal("0.029"), fx_loss_rate=Decimal("0.015"), tariff_rate=Decimal("0.05"), return_rate=Decimal("0.08"), return_shipping_nonrecoverable=Decimal("2"), other_variable_cost=Decimal("0.35")),
        activity=PromotionActivityInput(platform="tiktok_shop", activity_name="Sale", discount_type="percentage", discount_value=Decimal("0.25"), extra_commission_rate=Decimal("0.03"), creator_commission_rate=Decimal("0.12"), estimated_sales=500),
    )

