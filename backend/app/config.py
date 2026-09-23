from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "CrossProfit AI"
    database_url: str = os.getenv("CROSSPROFIT_DB_URL", f"sqlite:///{ROOT_DIR / 'data' / 'crossprofit.db'}")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY") or None
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    risk_thresholds: tuple[tuple[str, Decimal], ...] = (
        ("HIGHLY_RECOMMENDED", Decimal("0.20")),
        ("RECOMMENDED", Decimal("0.10")),
        ("CAUTION", Decimal("0.03")),
        ("NOT_RECOMMENDED", Decimal("0")),
    )


settings = Settings()
