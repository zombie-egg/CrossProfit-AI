from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HistoricalMetric, Merchant
from .auth import encrypt_secret, require_merchant

router = APIRouter(tags=["merchant"], dependencies=[Depends(require_merchant)])

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
        value = value.strip().lower().replace(" ", "_")
        if not re.fullmatch(r"[a-z0-9_]{2,64}", value):
            raise ValueError("平台标识只能使用英文、数字和下划线")
        return value


class AIKeyInput(BaseModel):
    api_key: str | None = Field(default=None, max_length=512)


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
