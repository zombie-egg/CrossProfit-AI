from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purchase_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    packaging_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    volume_cm3: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    platform_configs: Mapped[list["ProductPlatformConfig"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductPlatformConfig(Base):
    __tablename__ = "product_platform_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    original_price: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    platform_commission_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=0)
    creator_commission_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=0)
    payment_fee_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=0)
    fx_loss_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=0)
    tariff_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=0)
    tariff_basis: Mapped[str] = mapped_column(String(24), default="product_cost")
    return_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=0)
    return_shipping_nonrecoverable: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    return_product_loss_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=Decimal("0.35"))
    platform_nonrefundable_fee_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), default=0)
    other_variable_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    demo_default: Mapped[bool] = mapped_column(default=True)
    product: Mapped[Product] = relationship(back_populates="platform_configs")


class PromotionActivity(Base):
    __tablename__ = "promotion_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    activity_name: Mapped[str] = mapped_column(String(160))
    activity_type: Mapped[str] = mapped_column(String(50), default="promotion")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(30), default="none")
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 5), default=0)
    estimated_sales: Mapped[int] = mapped_column(Integer, default=100)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parse_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("promotion_activities.id"), index=True)
    unit_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(9, 5))
    estimated_total_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    risk_level: Mapped[str] = mapped_column(String(32))
    result_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scenarios: Mapped[list["ScenarioResult"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class ScenarioResult(Base):
    __tablename__ = "scenario_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id", ondelete="CASCADE"), index=True)
    scenario_name: Mapped[str] = mapped_column(String(30))
    unit_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(9, 5))
    assumptions: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[AnalysisResult] = relationship(back_populates="scenarios")

