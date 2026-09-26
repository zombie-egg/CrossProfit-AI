from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HistoricalMetric, Merchant, PlatformConnection
from .auth import encrypt_secret, require_merchant

router = APIRouter(tags=["merchant"], dependencies=[Depends(require_merchant)])

PLATFORMS = [
    {"id": "tiktok_shop", "name": "TikTok Shop", "region": "Global"},
    {"id": "amazon", "name": "Amazon", "region": "Global"},
]


class ConnectionInput(BaseModel):
    platform: str = Field(max_length=64)
    label: str = Field(min_length=1, max_length=120)
    shop_id: str | None = Field(default=None, max_length=120)
    app_key: str | None = Field(default=None, max_length=512)
    app_secret: str | None = Field(default=None, max_length=1024)
    access_token: str | None = Field(default=None, max_length=2048)

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        value = value.strip().lower().replace(" ", "_")
        if not re.fullmatch(r"[a-z0-9_]{2,64}", value):
            raise ValueError("平台标识只能使用英文、数字和下划线")
        return value


class HistoricalInput(BaseModel):
    platform: str = Field(max_length=64)
    period: str = Field(min_length=1, max_length=100)
    visitors: int | None = Field(default=None, ge=0)
    orders: int | None = Field(default=None, ge=0)
    returns: int | None = Field(default=None, ge=0)
    source: str = Field(min_length=1, max_length=200)

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        return ConnectionInput.normalize_platform(value)


class AIKeyInput(BaseModel):
    api_key: str | None = Field(default=None, max_length=512)


def connection_public(row: PlatformConnection) -> dict:
    return {"id": row.id, "platform": row.platform, "label": row.label, "shop_id": row.shop_id,
            "has_app_key": bool(row.app_key_encrypted), "has_app_secret": bool(row.app_secret_encrypted),
            "has_access_token": bool(row.access_token_encrypted), "status": row.status,
            "created_at": row.created_at.isoformat()}


@router.get("/platform-catalog")
def platform_catalog():
    return PLATFORMS


@router.get("/connections")
def list_connections(merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    return [connection_public(row) for row in db.scalars(select(PlatformConnection).where(PlatformConnection.merchant_id == merchant.id).order_by(PlatformConnection.id.desc()))]


@router.post("/connections", status_code=201)
def create_connection(payload: ConnectionInput, merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    if payload.platform not in {"tiktok_shop", "amazon"}:
        raise HTTPException(422, "目前仅支持 TikTok Shop 与 Amazon")
    if db.scalar(select(PlatformConnection.id).where(PlatformConnection.merchant_id == merchant.id, PlatformConnection.platform == payload.platform, PlatformConnection.label == payload.label)):
        raise HTTPException(409, "该平台连接名称已存在")
    row = PlatformConnection(merchant_id=merchant.id, platform=payload.platform, label=payload.label, shop_id=payload.shop_id,
                             app_key_encrypted=encrypt_secret(payload.app_key), app_secret_encrypted=encrypt_secret(payload.app_secret),
                             access_token_encrypted=encrypt_secret(payload.access_token), status="credentials_saved" if any((payload.app_key, payload.app_secret, payload.access_token)) else "awaiting_credentials")
    db.add(row)
    db.commit()
    db.refresh(row)
    return connection_public(row)


@router.put("/connections/{connection_id}")
def update_connection(connection_id: int, payload: ConnectionInput, merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    if payload.platform not in {"tiktok_shop", "amazon"}:
        raise HTTPException(422, "目前仅支持 TikTok Shop 与 Amazon")
    row = db.scalar(select(PlatformConnection).where(PlatformConnection.id == connection_id, PlatformConnection.merchant_id == merchant.id))
    if row is None:
        raise HTTPException(404, "平台连接不存在")
    row.platform, row.label, row.shop_id = payload.platform, payload.label, payload.shop_id
    if payload.app_key is not None:
        row.app_key_encrypted = encrypt_secret(payload.app_key)
    if payload.app_secret is not None:
        row.app_secret_encrypted = encrypt_secret(payload.app_secret)
    if payload.access_token is not None:
        row.access_token_encrypted = encrypt_secret(payload.access_token)
    row.status = "credentials_saved" if any((row.app_key_encrypted, row.app_secret_encrypted, row.access_token_encrypted)) else "awaiting_credentials"
    db.commit()
    return connection_public(row)


@router.delete("/connections/{connection_id}", status_code=204)
def delete_connection(connection_id: int, merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    row = db.scalar(select(PlatformConnection).where(PlatformConnection.id == connection_id, PlatformConnection.merchant_id == merchant.id))
    if row is None:
        raise HTTPException(404, "平台连接不存在")
    db.delete(row)
    db.commit()


@router.get("/ai/key")
def ai_key_status(merchant: Merchant = Depends(require_merchant)):
    return {"configured": bool(merchant.deepseek_key_encrypted)}


@router.put("/ai/key")
def save_ai_key(payload: AIKeyInput, merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    merchant.deepseek_key_encrypted = encrypt_secret(payload.api_key.strip()) if payload.api_key else None
    db.commit()
    return {"configured": bool(merchant.deepseek_key_encrypted)}


@router.get("/historical-metrics")
def list_historical_metrics(merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    rows = db.scalars(select(HistoricalMetric).where(HistoricalMetric.merchant_id == merchant.id).order_by(HistoricalMetric.id.desc())).all()
    return [{"id": row.id, "platform": row.platform, "period": row.period, "visitors": row.visitors,
             "orders": row.orders, "returns": row.returns, "source": row.source} for row in rows]


@router.post("/historical-metrics", status_code=201)
def add_historical_metric(payload: HistoricalInput, merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    if payload.visitors is not None and payload.orders is not None and payload.orders > payload.visitors:
        raise HTTPException(422, "订单数不能超过同口径访客数")
    if payload.orders is not None and payload.returns is not None and payload.returns > payload.orders:
        raise HTTPException(422, "退货数不能超过同口径订单数")
    row = HistoricalMetric(merchant_id=merchant.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, **payload.model_dump()}
