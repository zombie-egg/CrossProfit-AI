from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MoneyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductInput(MoneyModel):
    name: str
    sku: str
    category: str = "uncategorized"
    purchase_cost: Decimal = Decimal("0")
    packaging_cost: Decimal = Decimal("0")
    weight_kg: Decimal = Decimal("0")
    volume_cm3: Decimal = Decimal("0")
    currency: str = "USD"


class PlatformConfigInput(MoneyModel):
    platform: str
    original_price: Decimal
    shipping_cost: Decimal = Decimal("0")
    platform_commission_rate: Decimal = Decimal("0")
    creator_commission_rate: Decimal = Decimal("0")
    payment_fee_rate: Decimal = Decimal("0")
    fx_loss_rate: Decimal = Decimal("0")
    tariff_rate: Decimal = Decimal("0")
    tariff_basis: Literal["product_cost", "selling_price"] = "product_cost"
    return_rate: Decimal = Decimal("0")
    return_shipping_nonrecoverable: Decimal = Decimal("0")
    return_product_loss_rate: Decimal = Decimal("0.35")
    platform_nonrefundable_fee_rate: Decimal = Decimal("0")
    other_variable_cost: Decimal = Decimal("0")
    demo_default: bool = True

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    @field_validator("platform_commission_rate", "creator_commission_rate", "payment_fee_rate", "fx_loss_rate", "tariff_rate", "return_rate", "return_product_loss_rate", "platform_nonrefundable_fee_rate")
    @classmethod
    def validate_rate(cls, value: Decimal) -> Decimal:
        if not Decimal("0") <= value <= Decimal("1"):
            raise ValueError("费率必须使用 0 到 1 的小数，例如 15% = 0.15")
        return value


class PromotionActivityInput(MoneyModel):
    platform: str
    activity_name: str = "未命名活动"
    activity_type: str = "promotion"
    source_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    discount_type: Literal["percentage", "fixed_amount", "fixed_price", "none"] = "none"
    discount_value: Decimal = Decimal("0")
    minimum_discount: Decimal | None = None
    platform_commission_rate: Decimal | None = None
    extra_commission_rate: Decimal = Decimal("0")
    creator_commission_rate: Decimal | None = None
    shipping_subsidy: Decimal = Decimal("0")
    seller_shipping_cost: Decimal | None = None
    platform_subsidy: Decimal = Decimal("0")
    coupon_cost_bearer: str = "seller"
    coupon_amount: Decimal = Decimal("0")
    minimum_price_requirement: Decimal | None = None
    minimum_stock_requirement: int | None = None
    estimated_traffic_lift: Decimal | None = None
    estimated_sales: int = 100
    return_rate_override: Decimal | None = None
    currency: str = "USD"
    notes: str = ""
    raw_text: str = ""
    parse_confidence: Decimal = Decimal("0")
    missing_fields: list[str] = Field(default_factory=list)
    registration_fee: Decimal = Decimal("0")
    ad_budget: Decimal = Decimal("0")
    creative_cost: Decimal = Decimal("0")
    creator_fixed_fee: Decimal = Decimal("0")

    @property
    def fixed_cost(self) -> Decimal:
        return self.registration_fee + self.ad_budget + self.creative_cost + self.creator_fixed_fee

    @field_validator("discount_value")
    @classmethod
    def validate_discount(cls, value: Decimal, info) -> Decimal:
        # fixed_amount/fixed_price may exceed 1; percentage is validated by the engine adapter/UI path.
        if value < 0:
            raise ValueError("折扣值不能为负数")
        return value

    @field_validator("platform_commission_rate", "extra_commission_rate", "creator_commission_rate", "return_rate_override")
    @classmethod
    def validate_optional_rate(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not Decimal("0") <= value <= Decimal("1"):
            raise ValueError("费率必须使用 0 到 1 的小数")
        return value

    @model_validator(mode="after")
    def validate_percentage_discount(self):
        if self.discount_type == "percentage" and self.discount_value > Decimal("1"):
            raise ValueError("百分比折扣必须使用 0 到 1 的小数，例如 25% = 0.25")
        if self.estimated_sales < 0:
            raise ValueError("预计销量不能为负数")
        return self


class ProfitAnalysisRequest(MoneyModel):
    product: ProductInput
    platform_config: PlatformConfigInput
    activity: PromotionActivityInput
    rate_source: str | None = None
    rate_effective_date: date | None = None


class PortfolioItemInput(MoneyModel):
    product_id: int
    platform_config: PlatformConfigInput
    estimated_sales: int = Field(ge=0)


class PortfolioRequest(MoneyModel):
    activity: PromotionActivityInput
    items: list[PortfolioItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("组合内商品不能重复")
        return self


class CalculationBreakdown(MoneyModel):
    item: str
    formula: str
    input_values: dict[str, Any]
    amount: Decimal
    description: str


class ProfitResult(MoneyModel):
    original_price: Decimal
    discount_amount: Decimal
    selling_price: Decimal
    revenue: Decimal
    total_cost: Decimal
    unit_profit: Decimal
    profit_margin: Decimal
    estimated_sales: int
    estimated_revenue: Decimal
    estimated_total_profit: Decimal
    break_even_price: Decimal | None
    break_even_quantity: int | None
    fixed_cost: Decimal
    risk_level: str
    risk_label: str
    assumptions: list[str]
    breakdown: list[CalculationBreakdown]


class ScenarioResult(MoneyModel):
    name: str
    sales_multiplier: Decimal
    return_rate: Decimal
    shipping_multiplier: Decimal
    unit_profit: Decimal
    profit_margin: Decimal
    total_profit: Decimal
    profitable: bool
    sample_size: int | None = None
    source: Literal["calibrated", "default"] = "default"
    confidence_note: str | None = None


class ParsedPromotion(MoneyModel):
    activity: PromotionActivityInput
    recognized_fields: dict[str, Any]
    missing_suggestions: list[dict[str, str]]
    fetch_warning: str | None = None
