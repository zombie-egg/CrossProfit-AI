from __future__ import annotations

from io import BytesIO
from decimal import Decimal
import json
import secrets
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ..database import SNAPSHOT_CASCADE_KEY, get_db
from ..config import settings
from ..models import AnalysisResult as AnalysisRecord
from ..models import ForecastSnapshot, Product, ProductPlatformConfig, PromotionActivity, ReconciliationReport, SettlementImport, ScenarioResult as ScenarioRecord
from ..models import Merchant
from .auth import decrypt_secret, require_merchant
from ..schemas.domain import ParsedPromotion, PlatformConfigInput, PortfolioRequest, ProductInput, ProfitAnalysisRequest, ProfitResult, PromotionActivityInput
from ..services.factories import request_from_models
from ..services.llm import llm_status
from ..services.export_service import ExportService
from ..services.profit_engine import ProfitEngine
from ..services.portfolio_engine import analyze_portfolio
from ..services.calibration import calibrate, calibrated_for
from ..services.promotion_parser import PromotionParserService
from ..services.scenario_engine import ScenarioEngine
from ..services.reconciliation.amazon import AmazonSettlementParser
from ..services.reconciliation.tiktok import TikTokSettlementParser
from ..services.reconciliation.base import MAX_BYTES, SettlementLine, SettlementParseError
from ..services.reconciliation.mapper import normalize_fees
from ..services.reconciliation.engine import ReconciliationEngine
from ..services.strategy_engine import StrategyEngine

public_router = APIRouter()
router = APIRouter(dependencies=[Depends(require_merchant)])


def _settlement_parser(platform: str):
    parsers = {"tiktok_shop": TikTokSettlementParser, "amazon": AmazonSettlementParser}
    if platform not in parsers:
        raise HTTPException(422, "目前仅支持 TikTok Shop 与 Amazon 结算单")
    return parsers[platform]()


def _mapping(value: str) -> dict:
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("映射必须是 JSON 对象")
        return parsed
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(422, f"映射配置无效：{exc}") from exc


async def _parse_upload(file: UploadFile, platform: str, mapping: dict):
    content = await file.read(MAX_BYTES + 1)
    try:
        return _settlement_parser(platform).parse(content, mapping)
    except SettlementParseError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/settlements/template/{platform}")
def settlement_template(platform: str):
    return _settlement_parser(platform).template()


@router.post("/settlements/import")
async def preview_settlement(platform: str = Form(...), file: UploadFile = File(...), column_mapping: str = Form("{}"), fee_mapping: str = Form("{}")):
    mapping, fee_map = _mapping(column_mapping), _mapping(fee_mapping)
    lines, unknown = await _parse_upload(file, platform, mapping)
    unmapped = [item for line in lines for item in normalize_fees(line, fee_map)[1]]
    return {"row_count": len(lines), "columns": list(lines[0].raw_row), "preview": [line.model_dump(mode="json") for line in lines[:5]],
        "unrecognized_columns": unknown, "unmapped_fees": unmapped, "column_mapping": mapping, "fee_mapping": fee_map,
        "message": "仅预览，尚未入库；请核对列和费项映射后确认。"}


@router.post("/settlements/confirm")
async def confirm_settlement(platform: str = Form(...), file: UploadFile = File(...), column_mapping: str = Form("{}"), fee_mapping: str = Form("{}"), db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    mapping, fee_map = _mapping(column_mapping), _mapping(fee_mapping)
    lines, unknown = await _parse_upload(file, platform, mapping)
    unmapped = [item for line in lines for item in normalize_fees(line, fee_map)[1]]
    row = SettlementImport(merchant_id=merchant.id, platform=platform, file_name=Path(file.filename or "settlement.csv").name[:255],
        row_count=len(lines), unmapped_count=len(unmapped), status="confirmed", lines_data=[line.model_dump(mode="json") for line in lines],
        column_mapping=mapping, fee_mapping=fee_map, unrecognized_columns=unknown)
    db.add(row); db.commit(); db.refresh(row)
    return {"import_id": row.id, "row_count": row.row_count, "unmapped_count": row.unmapped_count, "unrecognized_columns": unknown}


@router.post("/reconciliation/run")
def run_reconciliation(snapshot_id: int, import_id: int, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    snapshot = db.scalar(select(ForecastSnapshot).where(ForecastSnapshot.id == snapshot_id, ForecastSnapshot.merchant_id == merchant.id))
    imported = db.scalar(select(SettlementImport).where(SettlementImport.id == import_id, SettlementImport.merchant_id == merchant.id))
    if not snapshot or not imported:
        raise HTTPException(404, "快照或结算单不存在")
    if ProfitAnalysisRequest.model_validate(snapshot.snapshot_data).activity.platform != imported.platform:
        raise HTTPException(422, "结算单平台与快照平台不一致")
    result = ReconciliationEngine().run(snapshot.snapshot_data, [SettlementLine.model_validate(item) for item in imported.lines_data], imported.fee_mapping, imported.unrecognized_columns)
    row = ReconciliationReport(merchant_id=merchant.id, snapshot_id=snapshot.id, import_id=imported.id, **result)
    db.add(row); db.flush()
    request = ProfitAnalysisRequest.model_validate(snapshot.snapshot_data)
    calibrate(db, merchant.id, request.activity.platform, request.product.category)
    db.commit(); db.refresh(row)
    return {"id": row.id, **result}


@router.get("/reconciliation")
def reconciliation_history(db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    rows = db.scalars(select(ReconciliationReport).where(ReconciliationReport.merchant_id == merchant.id).order_by(ReconciliationReport.created_at.desc())).all()
    return [{"id": row.id, "snapshot_id": row.snapshot_id, "import_id": row.import_id, "formula_verdict": row.formula_verdict,
        "max_fee_diff": str(row.max_fee_diff), "created_at": row.created_at.isoformat()} for row in rows]


@router.get("/reconciliation/{report_id}")
def reconciliation_detail(report_id: int, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    row = db.scalar(select(ReconciliationReport).where(ReconciliationReport.id == report_id, ReconciliationReport.merchant_id == merchant.id))
    if not row:
        raise HTTPException(404, "对账报告不存在")
    return {"id": row.id, "snapshot_id": row.snapshot_id, "import_id": row.import_id, "formula_verdict": row.formula_verdict,
        "max_fee_diff": str(row.max_fee_diff), "forecast_diff": row.forecast_diff, "diff_data": row.diff_data, "created_at": row.created_at.isoformat()}


@router.get("/reconciliation/{report_id}/export")
def export_reconciliation(report_id: int, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    report = reconciliation_detail(report_id, db, merchant)
    data = ExportService().reconciliation_xlsx(report)
    return StreamingResponse(BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reconciliation-{report_id}.xlsx"})


@router.get("/forecasts")
def list_forecasts(db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    rows = db.scalars(select(ForecastSnapshot).where(ForecastSnapshot.merchant_id == merchant.id).order_by(ForecastSnapshot.frozen_at.desc())).all()
    return [{"id": row.id, "analysis_id": row.analysis_id, "product_id": row.product_id, "activity_id": row.activity_id,
        "sku": row.snapshot_data["product"]["sku"], "platform": row.snapshot_data["activity"]["platform"],
        "activity_name": row.snapshot_data["activity"]["activity_name"], "frozen_at": row.frozen_at.isoformat(),
        "engine_version": row.engine_version} for row in rows]


@public_router.get("/health")
def health():
    return {"status": "ok", "service": "CrossProfit AI"}


@router.get("/ai/status")
def ai_status(merchant: Merchant = Depends(require_merchant)):
    if merchant.deepseek_key_encrypted:
        return {"provider": "deepseek", "model": "merchant", "configured": True}
    return llm_status()


@router.get("/products")
def products(db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    rows = db.scalars(select(Product).where(Product.merchant_id == merchant.id).options(selectinload(Product.platform_configs))).all()
    return [{"id": p.id, "name": p.name, "sku": p.seller_sku, "category": p.category, "purchase_cost": str(p.purchase_cost), "packaging_cost": str(p.packaging_cost), "currency": p.currency, "platforms": [c.platform for c in p.platform_configs]} for p in rows]


@router.post("/products", status_code=201)
def create_product(payload: ProductInput, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    if db.scalar(select(Product).where(Product.merchant_id == merchant.id, Product.seller_sku == payload.sku)):
        raise HTTPException(409, "SKU 已存在")
    row = Product(**{key: value for key, value in payload.model_dump().items() if key != "sku"}, sku=secrets.token_hex(16), seller_sku=payload.sku, merchant_id=merchant.id)
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, **payload.model_dump(mode="json")}


def _product_detail(row: Product):
    return {
        "id": row.id, "name": row.name, "sku": row.seller_sku, "category": row.category, "purchase_cost": str(row.purchase_cost),
        "packaging_cost": str(row.packaging_cost), "weight_kg": str(row.weight_kg), "volume_cm3": str(row.volume_cm3),
        "currency": row.currency, "created_at": row.created_at.isoformat(),
        "platform_configs": [{column.name: (str(getattr(config, column.name)) if hasattr(getattr(config, column.name), "as_tuple") else getattr(config, column.name)) for column in ProductPlatformConfig.__table__.columns if column.name not in {"product_id"}} for config in row.platform_configs],
    }


@router.get("/products/{product_id}")
def product_detail(product_id: int, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    row = db.scalar(select(Product).where(Product.id == product_id, Product.merchant_id == merchant.id).options(selectinload(Product.platform_configs)))
    if not row:
        raise HTTPException(404, "商品不存在")
    return _product_detail(row)


@router.put("/products/{product_id}")
def update_product(product_id: int, payload: ProductInput, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    row = db.scalar(select(Product).where(Product.id == product_id, Product.merchant_id == merchant.id))
    if not row:
        raise HTTPException(404, "商品不存在")
    duplicate = db.scalar(select(Product).where(Product.merchant_id == merchant.id, Product.seller_sku == payload.sku, Product.id != product_id))
    if duplicate:
        raise HTTPException(409, "SKU 已存在")
    for key, value in payload.model_dump().items():
        setattr(row, "seller_sku" if key == "sku" else key, value)
    db.commit()
    return {"id": row.id, **payload.model_dump(mode="json")}


@router.post("/products/{product_id}/platform-configs", status_code=201)
def save_platform_config(product_id: int, payload: PlatformConfigInput, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    if not db.scalar(select(Product.id).where(Product.id == product_id, Product.merchant_id == merchant.id)):
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
def delete_product(product_id: int, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    row = db.scalar(select(Product).where(Product.id == product_id, Product.merchant_id == merchant.id))
    if not row:
        raise HTTPException(404, "商品不存在")
    activity_ids = list(db.scalars(select(PromotionActivity.id).where(PromotionActivity.product_id == product_id)))
    analysis_ids = list(db.scalars(select(AnalysisRecord.id).where(AnalysisRecord.product_id == product_id)))
    snapshots = db.scalars(select(ForecastSnapshot).where(ForecastSnapshot.product_id == product_id,
        ForecastSnapshot.merchant_id == merchant.id)).all()
    snapshot_ids = [snapshot.id for snapshot in snapshots]
    calibration_scopes = {(snapshot.snapshot_data["activity"]["platform"],
        snapshot.snapshot_data["product"].get("category", "uncategorized")) for snapshot in snapshots}
    if snapshot_ids:
        db.execute(delete(ReconciliationReport).where(ReconciliationReport.snapshot_id.in_(snapshot_ids),
            ReconciliationReport.merchant_id == merchant.id))
        connection = db.connection()
        previous = connection.info.get(SNAPSHOT_CASCADE_KEY)
        connection.info[SNAPSHOT_CASCADE_KEY] = product_id
        try:
            db.execute(delete(ForecastSnapshot).where(ForecastSnapshot.id.in_(snapshot_ids),
                ForecastSnapshot.product_id == product_id, ForecastSnapshot.merchant_id == merchant.id))
        finally:
            if previous is None:
                connection.info.pop(SNAPSHOT_CASCADE_KEY, None)
            else:
                connection.info[SNAPSHOT_CASCADE_KEY] = previous
    if analysis_ids:
        db.execute(delete(ScenarioRecord).where(ScenarioRecord.analysis_id.in_(analysis_ids)))
        db.execute(delete(AnalysisRecord).where(AnalysisRecord.id.in_(analysis_ids)))
    if activity_ids:
        db.execute(delete(PromotionActivity).where(PromotionActivity.id.in_(activity_ids)))
    for platform, category in calibration_scopes:
        calibrate(db, merchant.id, platform, category)
    db.delete(row); db.commit()


@router.get("/activities")
def activities(db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    return [{"id": a.id, "product_id": a.product_id, "platform": a.platform, "activity_name": a.activity_name, "estimated_sales": a.estimated_sales} for a in db.scalars(select(PromotionActivity).where(PromotionActivity.merchant_id == merchant.id).order_by(PromotionActivity.created_at.desc())).all()]


@router.get("/activities/{activity_id}")
def activity_detail(activity_id: int, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    row = db.scalar(select(PromotionActivity).where(PromotionActivity.id == activity_id, PromotionActivity.merchant_id == merchant.id))
    if not row:
        raise HTTPException(404, "活动不存在")
    return {column.name: (str(getattr(row, column.name)) if hasattr(getattr(row, column.name), "as_tuple") else getattr(row, column.name)) for column in PromotionActivity.__table__.columns}


@router.post("/activities", status_code=201)
def create_activity(product_id: int, payload: PromotionActivityInput, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    if not db.scalar(select(Product.id).where(Product.id == product_id, Product.merchant_id == merchant.id)):
        raise HTTPException(404, "商品不存在")
    parameters = {key: str(getattr(payload, key)) for key in ["platform_commission_rate", "extra_commission_rate", "creator_commission_rate", "shipping_subsidy", "seller_shipping_cost", "platform_subsidy", "coupon_amount", "return_rate_override", "registration_fee", "ad_budget", "creative_cost", "creator_fixed_fee"] if getattr(payload, key) is not None and getattr(payload, key) != 0}
    row = PromotionActivity(product_id=product_id, merchant_id=merchant.id, platform=payload.platform, activity_name=payload.activity_name, activity_type=payload.activity_type, source_url=payload.source_url, start_date=payload.start_date, end_date=payload.end_date, discount_type=payload.discount_type, discount_value=payload.discount_value, estimated_sales=payload.estimated_sales, currency=payload.currency, raw_text=payload.raw_text, parse_confidence=payload.parse_confidence, missing_fields=payload.missing_fields, parameters=parameters)
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


@router.post("/analysis/portfolio")
def portfolio_analysis(payload: PortfolioRequest, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    ids = [item.product_id for item in payload.items]
    rows = db.scalars(select(Product).where(Product.merchant_id == merchant.id, Product.id.in_(ids))).all()
    products = {row.id: ProductInput(name=row.name, sku=row.seller_sku or row.sku, purchase_cost=row.purchase_cost,
        packaging_cost=row.packaging_cost, weight_kg=row.weight_kg, volume_cm3=row.volume_cm3, currency=row.currency) for row in rows}
    if len(products) != len(ids):
        raise HTTPException(404, "组合商品不存在或不属于当前商家")
    if any(item.platform_config.platform != payload.activity.platform or products[item.product_id].currency != payload.activity.currency for item in payload.items):
        raise HTTPException(422, "组合内平台和币种必须与活动一致")
    return analyze_portfolio(payload, products)


@router.post("/analysis/run")
def run_analysis(payload: ProfitAnalysisRequest, product_id: int | None = None, activity_id: int | None = None, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    result = ProfitEngine().calculate(payload)
    scenarios = ScenarioEngine().analyze(payload, calibrated_for(db, merchant.id, payload.activity.platform, payload.product.category))
    _calibration_assumption(result, scenarios, payload)
    recommendations = StrategyEngine(decrypt_secret(merchant.deepseek_key_encrypted)).generate(payload, result, scenarios, merchant.locale)
    analysis_id = None
    product = db.scalar(select(Product).where(Product.id == product_id, Product.merchant_id == merchant.id)) if product_id is not None else None
    if product_id is not None and activity_id is not None and product and db.scalar(select(PromotionActivity.id).where(PromotionActivity.id == activity_id, PromotionActivity.merchant_id == merchant.id, PromotionActivity.product_id == product_id)):
        if payload.product.sku != (product.seller_sku or product.sku):
            raise HTTPException(422, "快照 SKU 与归档商品不一致")
        record = AnalysisRecord(product_id=product_id, activity_id=activity_id, merchant_id=merchant.id, unit_profit=result.unit_profit, profit_margin=result.profit_margin, estimated_total_profit=result.estimated_total_profit, risk_level=result.risk_level, result_data={"result": result.model_dump(mode="json"), "scenarios": [item.model_dump(mode="json") for item in scenarios], "recommendations": recommendations})
        db.add(record); db.flush()
        snapshot = _freeze_snapshot(db, payload, record, merchant.id)
        db.commit(); analysis_id = record.id
        return {"analysis_id": analysis_id, "snapshot_id": snapshot.id, "revision": _revision(db, snapshot), "result": result, "scenarios": scenarios, "recommendations": recommendations}
    return {"analysis_id": analysis_id, "result": result, "scenarios": scenarios, "recommendations": recommendations}


def _freeze_snapshot(db: Session, payload: ProfitAnalysisRequest, record: AnalysisRecord, merchant_id: int) -> ForecastSnapshot:
    snapshot = ForecastSnapshot(merchant_id=merchant_id, analysis_id=record.id, product_id=record.product_id,
        activity_id=record.activity_id, snapshot_data=payload.model_dump(mode="json"),
        engine_version=settings.engine_version, rate_source=payload.rate_source,
        rate_effective_date=payload.rate_effective_date, locked=True)
    db.add(snapshot)
    db.flush()
    return snapshot


def _revision(db: Session, snapshot: ForecastSnapshot) -> int:
    return len(db.scalars(select(ForecastSnapshot.id).where(ForecastSnapshot.merchant_id == snapshot.merchant_id,
        ForecastSnapshot.product_id == snapshot.product_id, ForecastSnapshot.activity_id == snapshot.activity_id)).all())


def _calibration_assumption(result: ProfitResult, scenarios: list, payload: ProfitAnalysisRequest) -> None:
    if scenarios and scenarios[0].source == "calibrated":
        result.assumptions.append(f"场景参数来源：本店铺 {payload.activity.platform}/{payload.product.category} 已对账订单；样本 {scenarios[0].sample_size} 单；统计窗口 90 天。")


@router.post("/analysis/archive")
def archive_analysis(payload: ProfitAnalysisRequest, product_id: int, activity_id: int | None = None, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    """Persist an activity and its analysis atomically after the user confirms the preview."""
    product = db.scalar(select(Product).where(Product.id == product_id, Product.merchant_id == merchant.id))
    if not product:
        raise HTTPException(404, "商品不存在")
    if payload.product.sku != (product.seller_sku or product.sku):
        raise HTTPException(422, "快照 SKU 与归档商品不一致")
    activity = db.get(PromotionActivity, activity_id) if activity_id is not None else None
    if activity_id is not None and (activity is None or activity.product_id != product_id or activity.merchant_id != merchant.id):
        raise HTTPException(404, "活动不存在或不属于当前商品")

    result = ProfitEngine().calculate(payload)
    scenarios = ScenarioEngine().analyze(payload, calibrated_for(db, merchant.id, payload.activity.platform, payload.product.category))
    _calibration_assumption(result, scenarios, payload)
    recommendations = StrategyEngine(decrypt_secret(merchant.deepseek_key_encrypted)).generate(payload, result, scenarios, merchant.locale)
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
            merchant_id=merchant.id,
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
        merchant_id=merchant.id,
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
    db.flush()
    snapshot = _freeze_snapshot(db, payload, record, merchant.id)
    revision = _revision(db, snapshot)
    db.commit()
    return {
        "analysis_id": record.id,
        "snapshot_id": snapshot.id,
        "revision": revision,
        "revision_message": f"第 {revision} 次修订，历史快照保留不变",
        "activity_id": activity.id,
        "result": result,
        "scenarios": scenarios,
        "recommendations": recommendations,
    }


@router.get("/analysis")
def analysis_history(db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    rows = db.execute(select(AnalysisRecord, Product, PromotionActivity).join(Product, Product.id == AnalysisRecord.product_id).join(PromotionActivity, PromotionActivity.id == AnalysisRecord.activity_id).where(AnalysisRecord.merchant_id == merchant.id, Product.merchant_id == merchant.id, PromotionActivity.merchant_id == merchant.id).order_by(AnalysisRecord.created_at.desc())).all()
    history = []
    for record, product, activity in rows:
        result = (record.result_data or {}).get("result", {})
        cost_drivers = sorted(
            (
                {"item": item.get("item", "其他费用"), "amount": str(item.get("amount", "0"))}
                for item in result.get("breakdown", [])
                if Decimal(str(item.get("amount", 0))) > 0
            ),
            key=lambda item: Decimal(item["amount"]),
            reverse=True,
        )[:2]
        history.append({
            "id": record.id,
            "activity_id": activity.id,
            "product_id": product.id,
            "activity_name": activity.activity_name,
            "product_name": product.name,
            "platform": activity.platform,
            "unit_profit": str(record.unit_profit),
            "profit_margin": str(record.profit_margin),
            "estimated_total_profit": str(record.estimated_total_profit),
            "risk_level": record.risk_level,
            "cost_drivers": cost_drivers,
            "created_at": record.created_at.isoformat(),
        })
    return history


@router.get("/ui/bootstrap")
def ui_bootstrap(db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    products = db.scalars(select(Product).where(Product.merchant_id == merchant.id).options(selectinload(Product.platform_configs)).order_by(Product.id)).all()
    activities = db.scalars(select(PromotionActivity).where(PromotionActivity.merchant_id == merchant.id).order_by(PromotionActivity.id)).all()
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
def get_analysis(analysis_id: int, db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    row = db.scalar(select(AnalysisRecord).where(AnalysisRecord.id == analysis_id, AnalysisRecord.merchant_id == merchant.id))
    if not row:
        raise HTTPException(404, "分析记录不存在")
    return row.result_data


@router.get("/export/{analysis_id}")
def export_analysis(analysis_id: int, format: str = "xlsx", db: Session = Depends(get_db), merchant: Merchant = Depends(require_merchant)):
    row = db.scalar(select(AnalysisRecord).where(AnalysisRecord.id == analysis_id, AnalysisRecord.merchant_id == merchant.id))
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
