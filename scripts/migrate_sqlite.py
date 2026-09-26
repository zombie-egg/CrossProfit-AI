"""Idempotent compatibility upgrade for existing SQLite databases.

Usage: python scripts/migrate_sqlite.py data/crossprofit.db
Run after backing up the database and before restarting the application.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


ADDED_COLUMNS = {
    "products": {"merchant_id": "INTEGER", "seller_sku": "VARCHAR(64)", "category": "VARCHAR(120) DEFAULT 'uncategorized'"},
    "promotion_activities": {"merchant_id": "INTEGER"},
    "analysis_results": {"merchant_id": "INTEGER"},
    "settlement_imports": {"unrecognized_columns": "JSON DEFAULT '[]'"},
    "calibrated_parameters": {"report_count": "INTEGER DEFAULT 0"},
}


def migrate(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    with sqlite3.connect(path) as db:
        for table, columns in ADDED_COLUMNS.items():
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                continue
            existing = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
            for name, column_type in columns.items():
                if name not in existing:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='platform_connections'").fetchone():
            db.execute("UPDATE platform_connections SET status = 'deprecated' WHERE platform NOT IN ('tiktok_shop', 'amazon') AND status != 'deprecated'")


if __name__ == "__main__":
    migrate(Path(sys.argv[1] if len(sys.argv) > 1 else "data/crossprofit.db"))
