from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import AnalysisResult as AnalysisRecord
from ..models import Product, ProductPlatformConfig, PromotionActivity, ScenarioResult as ScenarioRecord
from ..schemas.domain import ParsedPromotion, PlatformConfigInput, ProductInput, ProfitAnalysisRequest, ProfitResult, PromotionActivityInput
from ..services.factories import request_from_models
from ..services.export_service import ExportService
from ..services.profit_engine import ProfitEngine
from ..services.promotion_parser import PromotionParserService
from ..services.scenario_engine import ScenarioEngine
from ..services.strategy_engine import StrategyEngine

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "CrossProfit AI"}


@router.get("/products")
def products(db: Session = Depends(get_db)):
    rows = db.scalars(select(Product).options(selectinload(Product.platform_configs))).all()
    return [{"id": p.id, "name": p.name, "sku": p.sku, "purchase_cost": str(p.purchase_cost), "packaging_cost": str(p.packaging_cost), "currency": p.currency, "platforms": [c.platform for c in p.platform_configs]} for p in rows]


@router.post("/products", status_code=201)
def create_product(payload: ProductInput, db: Session = Depends(get_db)):
    if db.scalar(select(Product).where(Product.sku == payload.sku)):
        raise HTTPException(409, "SKU 已存在")
    row = Product(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, **payload.model_dump(mode="json")}


def _product_detail(row: Product):
    return {
        "id": row.id, "name": row.name, "sku": row.sku, "purchase_cost": str(row.purchase_cost),
        "packaging_cost": str(row.packaging_cost), "weight_kg": str(row.weight_kg), "volume_cm3": str(row.volume_cm3),
        "currency": row.currency, "created_at": row.created_at.isoformat(),
        "platform_configs": [{column.name: (str(getattr(config, column.name)) if hasattr(getattr(config, column.name), "as_tuple") else getattr(config, column.name)) for column in ProductPlatformConfig.__table__.columns if column.name not in {"product_id"}} for config in row.platform_configs],
    }


@router.get("/products/{product_id}")
def product_detail(product_id: int, db: Session = Depends(get_db)):
    row = db.scalar(select(Product).where(Product.id == product_id).options(selectinload(Product.platform_configs)))
    if not row:
        raise HTTPException(404, "商品不存在")
    return _product_detail(row)


@router.put("/products/{product_id}")
def update_product(product_id: int, payload: ProductInput, db: Session = Depends(get_db)):
    row = db.get(Product, product_id)
    if not row:
        raise HTTPException(404, "商品不存在")
    duplicate = db.scalar(select(Product).where(Product.sku == payload.sku, Product.id != product_id))
    if duplicate:
        raise HTTPException(409, "SKU 已存在")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return {"id": row.id, **payload.model_dump(mode="json")}


@router.post("/products/{product_id}/platform-configs", status_code=201)
def save_platform_config(product_id: int, payload: PlatformConfigInput, db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(404, "商品不存在")
    row = db.scalar(select(ProductPlatformConfig).where(ProductPlatformConfig.product_id == product_id, ProductPlatformConfig.platform == payload.platform))
    if row is None:
        row = ProductPlatformConfig(product_id=product_id)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit(); db.refresh(row)
    return {"id": row.id, **payload.model_dump(mode="json")}


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    row = db.get(Product, product_id)
    if not row:
        raise HTTPException(404, "商品不存在")
    activity_ids = list(db.scalars(select(PromotionActivity.id).where(PromotionActivity.product_id == product_id)))
    analysis_ids = list(db.scalars(select(AnalysisRecord.id).where(AnalysisRecord.product_id == product_id)))
    if analysis_ids:
        db.execute(delete(ScenarioRecord).where(ScenarioRecord.analysis_id.in_(analysis_ids)))
        db.execute(delete(AnalysisRecord).where(AnalysisRecord.id.in_(analysis_ids)))
    if activity_ids:
        db.execute(delete(PromotionActivity).where(PromotionActivity.id.in_(activity_ids)))
    db.delete(row); db.commit()


@router.get("/activities")
def activities(db: Session = Depends(get_db)):
    return [{"id": a.id, "product_id": a.product_id, "platform": a.platform, "activity_name": a.activity_name, "estimated_sales": a.estimated_sales} for a in db.scalars(select(PromotionActivity).order_by(PromotionActivity.created_at.desc())).all()]


@router.get("/activities/{activity_id}")
def activity_detail(activity_id: int, db: Session = Depends(get_db)):
    row = db.get(PromotionActivity, activity_id)
    if not row:
        raise HTTPException(404, "活动不存在")
    return {column.name: (str(getattr(row, column.name)) if hasattr(getattr(row, column.name), "as_tuple") else getattr(row, column.name)) for column in PromotionActivity.__table__.columns}


@router.post("/activities", status_code=201)
def create_activity(product_id: int, payload: PromotionActivityInput, db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(404, "商品不存在")
    parameters = {key: str(getattr(payload, key)) for key in ["platform_commission_rate", "extra_commission_rate", "creator_commission_rate", "shipping_subsidy", "seller_shipping_cost", "platform_subsidy", "coupon_amount", "return_rate_override", "registration_fee", "ad_budget", "creative_cost", "creator_fixed_fee"] if getattr(payload, key) is not None and getattr(payload, key) != 0}
    row = PromotionActivity(product_id=product_id, platform=payload.platform, activity_name=payload.activity_name, activity_type=payload.activity_type, source_url=payload.source_url, start_date=payload.start_date, end_date=payload.end_date, discount_type=payload.discount_type, discount_value=payload.discount_value, estimated_sales=payload.estimated_sales, currency=payload.currency, raw_text=payload.raw_text, parse_confidence=payload.parse_confidence, missing_fields=payload.missing_fields, parameters=parameters)
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "product_id": product_id}


@router.post("/activities/parse", response_model=ParsedPromotion)
def parse_activity(url: str | None = None, raw_text: str = "", platform_hint: str | None = None):
    return PromotionParserService().parse(url=url, raw_text=raw_text, platform_hint=platform_hint)


@router.post("/analysis/profit", response_model=ProfitResult)
def analyze_profit(payload: ProfitAnalysisRequest):
    return ProfitEngine().calculate(payload)


@router.post("/analysis/compare")
def compare(payloads: list[ProfitAnalysisRequest]):
    engine = ProfitEngine()
    results = [engine.calculate(item) for item in payloads]
    return sorted(results, key=lambda x: x.estimated_total_profit, reverse=True)


@router.post("/analysis/run")
def run_analysis(payload: ProfitAnalysisRequest, product_id: int | None = None, activity_id: int | None = None, db: Session = Depends(get_db)):
    result = ProfitEngine().calculate(payload)
    scenarios = ScenarioEngine().analyze(payload)
    recommendations = StrategyEngine().generate(payload, result, scenarios)
    analysis_id = None
    if product_id is not None and activity_id is not None and db.get(Product, product_id) and db.get(PromotionActivity, activity_id):
        record = AnalysisRecord(product_id=product_id, activity_id=activity_id, unit_profit=result.unit_profit, profit_margin=result.profit_margin, estimated_total_profit=result.estimated_total_profit, risk_level=result.risk_level, result_data={"result": result.model_dump(mode="json"), "scenarios": [item.model_dump(mode="json") for item in scenarios], "recommendations": recommendations})
        db.add(record); db.commit(); db.refresh(record); analysis_id = record.id
    return {"analysis_id": analysis_id, "result": result, "scenarios": scenarios, "recommendations": recommendations}


@router.post("/analysis/archive")
def archive_analysis(payload: ProfitAnalysisRequest, product_id: int, activity_id: int | None = None, db: Session = Depends(get_db)):
    """Persist an activity and its analysis atomically after the user confirms the preview."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "商品不存在")
    activity = db.get(PromotionActivity, activity_id) if activity_id is not None else None
    if activity_id is not None and (activity is None or activity.product_id != product_id):
        raise HTTPException(404, "活动不存在或不属于当前商品")

    result = ProfitEngine().calculate(payload)
    scenarios = ScenarioEngine().analyze(payload)
    recommendations = StrategyEngine().generate(payload, result, scenarios)
    if activity is None:
        activity_payload = payload.activity
        parameters = {
            key: str(getattr(activity_payload, key))
            for key in [
                "platform_commission_rate", "extra_commission_rate", "creator_commission_rate",
                "shipping_subsidy", "seller_shipping_cost", "platform_subsidy", "coupon_amount",
                "return_rate_override", "registration_fee", "ad_budget", "creative_cost", "creator_fixed_fee",
            ]
            if getattr(activity_payload, key) is not None and getattr(activity_payload, key) != 0
        }
        activity = PromotionActivity(
            product_id=product_id,
            platform=activity_payload.platform,
            activity_name=activity_payload.activity_name,
            activity_type=activity_payload.activity_type,
            source_url=activity_payload.source_url,
            start_date=activity_payload.start_date,
            end_date=activity_payload.end_date,
            discount_type=activity_payload.discount_type,
            discount_value=activity_payload.discount_value,
            estimated_sales=activity_payload.estimated_sales,
            currency=activity_payload.currency,
            raw_text=activity_payload.raw_text,
            parse_confidence=activity_payload.parse_confidence,
            missing_fields=activity_payload.missing_fields,
            parameters=parameters,
        )
        db.add(activity)
        db.flush()

    record = AnalysisRecord(
        product_id=product_id,
        activity_id=activity.id,
        unit_profit=result.unit_profit,
        profit_margin=result.profit_margin,
        estimated_total_profit=result.estimated_total_profit,
        risk_level=result.risk_level,
        result_data={
            "result": result.model_dump(mode="json"),
            "scenarios": [item.model_dump(mode="json") for item in scenarios],
            "recommendations": recommendations,
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "analysis_id": record.id,
        "activity_id": activity.id,
        "result": result,
        "scenarios": scenarios,
        "recommendations": recommendations,
    }


@router.get("/analysis")
def analysis_history(db: Session = Depends(get_db)):
    rows = db.execute(select(AnalysisRecord, Product, PromotionActivity).join(Product, Product.id == AnalysisRecord.product_id).join(PromotionActivity, PromotionActivity.id == AnalysisRecord.activity_id).order_by(AnalysisRecord.created_at.desc())).all()
    return [{"id": record.id, "activity_id": activity.id, "product_id": product.id, "activity_name": activity.activity_name, "product_name": product.name, "platform": activity.platform, "unit_profit": str(record.unit_profit), "profit_margin": str(record.profit_margin), "estimated_total_profit": str(record.estimated_total_profit), "risk_level": record.risk_level, "created_at": record.created_at.isoformat()} for record, product, activity in rows]


@router.get("/ui/bootstrap")
def ui_bootstrap(db: Session = Depends(get_db)):
    products = db.scalars(select(Product).options(selectinload(Product.platform_configs)).order_by(Product.id)).all()
    activities = db.scalars(select(PromotionActivity).order_by(PromotionActivity.id)).all()
    cases = []
    product_map = {item.id: item for item in products}
    for activity in activities:
        product = product_map.get(activity.product_id)
        config = next((item for item in (product.platform_configs if product else []) if item.platform == activity.platform), None)
        if not product or not config:
            continue
        request = request_from_models(product, config, activity)
        result = ProfitEngine().calculate(request)
        cases.append({"id": activity.id, "product_id": product.id, "request": request.model_dump(mode="json"), "result": result.model_dump(mode="json")})
    return {"products": [_product_detail(item) for item in products], "cases": cases}


@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    row = db.get(AnalysisRecord, analysis_id)
    if not row:
        raise HTTPException(404, "分析记录不存在")
    return row.result_data


@router.get("/export/{analysis_id}")
def export_analysis(analysis_id: int, format: str = "xlsx", db: Session = Depends(get_db)):
    row = db.get(AnalysisRecord, analysis_id)
    if not row:
        raise HTTPException(404, "分析记录不存在")
    payload = row.result_data or {}
    result = payload.get("result", payload)
    if format.lower() == "csv":
        data = pd.DataFrame([{k: v for k, v in result.items() if k not in {"breakdown", "assumptions"}}]).to_csv(index=False).encode("utf-8-sig")
        return StreamingResponse(BytesIO(data), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=analysis-{analysis_id}.csv"})
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([{k: v for k, v in result.items() if k not in {"breakdown", "assumptions"}}]).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame(result.get("breakdown", [])).to_excel(writer, sheet_name="Cost Breakdown", index=False)
        pd.DataFrame(payload.get("scenarios", [])).to_excel(writer, sheet_name="Scenario Analysis", index=False)
        pd.DataFrame({"Recommendations": payload.get("recommendations", [])}).to_excel(writer, sheet_name="Recommendations", index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=analysis-{analysis_id}.xlsx"})
