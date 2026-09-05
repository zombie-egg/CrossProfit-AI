"""保留界面的独立 Streamlit 启动入口。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    if sys.version_info < (3, 11):
        print("CrossProfit AI 需要 Python 3.11+")
        return 1
    os.chdir(ROOT)
    from backend.app.database import init_db, session_scope
    from backend.app.services.demo_data import seed_demo_data

    init_db()
    with session_scope() as session:
        seed_demo_data(session)
    port = os.getenv("CROSSPROFIT_PORT", "8501")
    host = os.getenv("CROSSPROFIT_HOST", "127.0.0.1")
    return subprocess.call([
        sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py",
        "--server.address", host, "--server.port", port, "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])


if __name__ == "__main__":
    raise SystemExit(main())
