from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CalibratedParameter, ForecastSnapshot, ReconciliationReport
from .profit_engine import rate

WINDOW_DAYS = 90
MIN_ORDERS = 20
MIN_REPORTS = 3


def percentile(values: list[Decimal], fraction: Decimal) -> Decimal:
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return rate(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def calibrate(db: Session, merchant_id: int, platform: str, category: str) -> dict[str, CalibratedParameter]:
    cutoff = datetime.utcnow() - timedelta(days=WINDOW_DAYS)
    pairs = db.execute(select(ReconciliationReport, ForecastSnapshot).join(ForecastSnapshot, ReconciliationReport.snapshot_id == ForecastSnapshot.id)
        .where(ReconciliationReport.merchant_id == merchant_id, ForecastSnapshot.merchant_id == merchant_id,
            ReconciliationReport.created_at >= cutoff).order_by(ReconciliationReport.created_at.desc())).all()
    seen: set[tuple[int, str]] = set()
    values: dict[str, list[Decimal]] = {"return_rate": [], "sales_multiplier": []}
    sample_size = 0
    report_count = 0
    for report, snapshot in pairs:
        key = (report.import_id, snapshot.snapshot_data["product"]["sku"])
        if key in seen or snapshot.snapshot_data["activity"]["platform"] != platform or snapshot.snapshot_data["product"].get("category", "uncategorized") != category:
            continue
        seen.add(key)
        accuracy = report.forecast_diff
        actual = int(accuracy["actual_sales"])
        estimated = int(accuracy["estimated_sales"])
        if actual <= 0 or estimated <= 0 or accuracy["actual_return_rate"] is None:
            continue
        report_count += 1
        sample_size += actual
        values["return_rate"].append(Decimal(str(accuracy["actual_return_rate"])))
        values["sales_multiplier"].append(Decimal(actual) / Decimal(estimated))
    result: dict[str, CalibratedParameter] = {}
    if not report_count:
        return result
    for parameter, samples in values.items():
        row = db.scalar(select(CalibratedParameter).where(CalibratedParameter.merchant_id == merchant_id,
            CalibratedParameter.platform == platform, CalibratedParameter.category == category, CalibratedParameter.parameter == parameter))
        if row is None:
            row = CalibratedParameter(merchant_id=merchant_id, platform=platform, category=category, parameter=parameter)
            db.add(row)
        row.p25 = percentile(samples, Decimal("0.25"))
        row.p50 = percentile(samples, Decimal("0.50"))
        row.p75 = percentile(samples, Decimal("0.75"))
        row.sample_size = sample_size
        row.report_count = report_count
        row.window_days = WINDOW_DAYS
        row.updated_at = datetime.utcnow()
        result[parameter] = row
    db.flush()
    return result


def calibrated_for(db: Session, merchant_id: int, platform: str, category: str) -> dict[str, CalibratedParameter]:
    return {row.parameter: row for row in db.scalars(select(CalibratedParameter).where(CalibratedParameter.merchant_id == merchant_id,
        CalibratedParameter.platform == platform, CalibratedParameter.category == category)).all()}
