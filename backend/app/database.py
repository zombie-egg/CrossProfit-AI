from __future__ import annotations

from contextlib import contextmanager
import time

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

SNAPSHOT_CASCADE_KEY = "forecast_snapshot_cascade_product"


def register_snapshot_cleanup(db_engine):
    @event.listens_for(db_engine, "connect")
    def _register(dbapi_connection, connection_record):
        dbapi_connection.create_function("forecast_snapshot_cascade_product", 0,
            lambda: connection_record.info.get(SNAPSHOT_CASCADE_KEY))


def install_snapshot_guards(connection):
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS forecast_snapshots_no_update BEFORE UPDATE ON forecast_snapshots BEGIN SELECT RAISE(ABORT, 'forecast snapshot is immutable'); END"))
    connection.execute(text("DROP TRIGGER IF EXISTS forecast_snapshots_no_delete"))
    connection.execute(text("CREATE TRIGGER forecast_snapshots_no_delete BEFORE DELETE ON forecast_snapshots WHEN coalesce(forecast_snapshot_cascade_product(), -1) != OLD.product_id BEGIN SELECT RAISE(ABORT, 'forecast snapshot is immutable'); END"))


def build_engine(url: str | None = None):
    db_url = url or settings.database_url
    db_engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})
    if db_engine.dialect.name == "sqlite":
        register_snapshot_cleanup(db_engine)
    return db_engine


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    # create_all is idempotent, but two first-start processes can race between
    # SQLite's table-existence check and CREATE TABLE. Retry that narrow case.
    for attempt in range(4):
        try:
            Base.metadata.create_all(engine)
            if engine.dialect.name == "sqlite":
                with engine.begin() as connection:
                    inspector = inspect(connection)
                    for table, columns in {
                        "products": {"merchant_id": "INTEGER", "seller_sku": "VARCHAR(64)", "category": "VARCHAR(120) DEFAULT 'uncategorized'"},
                        "promotion_activities": {"merchant_id": "INTEGER"},
                        "analysis_results": {"merchant_id": "INTEGER"},
                        "settlement_imports": {"unrecognized_columns": "JSON DEFAULT '[]'"},
                        "calibrated_parameters": {"report_count": "INTEGER DEFAULT 0"},
                    }.items():
                        existing = {column["name"] for column in inspector.get_columns(table)}
                        for name, column_type in columns.items():
                            if name not in existing:
                                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_products_merchant_id ON products (merchant_id)"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_promotion_activities_merchant_id ON promotion_activities (merchant_id)"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_analysis_results_merchant_id ON analysis_results (merchant_id)"))
                    connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_products_merchant_seller_sku ON products (merchant_id, seller_sku)"))
                    connection.execute(text("UPDATE platform_connections SET status = 'deprecated' WHERE platform NOT IN ('tiktok_shop', 'amazon') AND status != 'deprecated'"))
                    install_snapshot_guards(connection)
            return
        except OperationalError as exc:
            if "already exists" not in str(exc).lower() or attempt == 3:
                raise
            time.sleep(0.05 * (attempt + 1))


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
