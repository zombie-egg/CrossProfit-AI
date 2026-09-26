from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    seller_sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(120), default="uncategorized")
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"), nullable=True, index=True)
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
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"), nullable=True, index=True)
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
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"), nullable=True, index=True)
    unit_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(9, 5))
    estimated_total_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    risk_level: Mapped[str] = mapped_column(String(32))
    result_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scenarios: Mapped[list["ScenarioResult"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("promotion_activities.id"), index=True)
    snapshot_data: Mapped[dict] = mapped_column(JSON)
    engine_version: Mapped[str] = mapped_column(String(32))
    rate_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    rate_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    frozen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    locked: Mapped[bool] = mapped_column(default=True)


@event.listens_for(ForecastSnapshot, "before_update")
@event.listens_for(ForecastSnapshot, "before_delete")
def _reject_snapshot_change(mapper, connection, target):
    raise ValueError("forecast snapshot is immutable")


class SettlementImport(Base):
    __tablename__ = "settlement_imports"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40))
    file_name: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer)
    unmapped_count: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="confirmed")
    lines_data: Mapped[list] = mapped_column(JSON)
    column_mapping: Mapped[dict] = mapped_column(JSON)
    fee_mapping: Mapped[dict] = mapped_column(JSON)
    unrecognized_columns: Mapped[list] = mapped_column(JSON, default=list)


class ReconciliationReport(Base):
    __tablename__ = "reconciliation_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("forecast_snapshots.id"), index=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("settlement_imports.id"), index=True)
    formula_verdict: Mapped[str] = mapped_column(String(8))
    max_fee_diff: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    forecast_diff: Mapped[dict] = mapped_column(JSON)
    diff_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CalibratedParameter(Base):
    __tablename__ = "calibrated_parameters"
    __table_args__ = (UniqueConstraint("merchant_id", "platform", "category", "parameter", name="uq_calibrated_scope"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(120))
    parameter: Mapped[str] = mapped_column(String(40))
    p25: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    p50: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    p75: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    sample_size: Mapped[int] = mapped_column(Integer)
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    window_days: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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


class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(String(5), default="zh")
    deepseek_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PricingTemplate(Base):
    __tablename__ = "pricing_templates"
    __table_args__ = (UniqueConstraint("merchant_id", "name", name="uq_pricing_template_merchant_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    platform: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(8))
    target_mode: Mapped[str] = mapped_column(String(20))
    target_value: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    defaults: Mapped[dict] = mapped_column(JSON)
    rate_source: Mapped[str] = mapped_column(Text)
    rate_effective_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    purpose: Mapped[str] = mapped_column(String(20))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[bool] = mapped_column(default=False)


class CaptchaChallenge(Base):
    __tablename__ = "captcha_challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    answer_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[bool] = mapped_column(default=False)


class MerchantSession(Base):
    __tablename__ = "merchant_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LoginFailure(Base):
    __tablename__ = "login_failures"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlatformConnection(Base):
    __tablename__ = "platform_connections"
    __table_args__ = (UniqueConstraint("merchant_id", "platform", "label", name="uq_merchant_platform_label"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(120))
    shop_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    app_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    app_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="credentials_saved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HistoricalMetric(Base):
    __tablename__ = "historical_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    period: Mapped[str] = mapped_column(String(100))
    visitors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    orders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    returns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
