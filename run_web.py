"""Launch the FastAPI backend and the competition Next.js interface together."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"


def main() -> int:
    if sys.version_info < (3, 11):
        print("CrossProfit AI 需要 Python 3.11+")
        return 1
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        print("未找到 npm，请安装 Node.js 18+。")
        return 1
    if not (WEB / "node_modules").exists():
        print("前端依赖尚未安装，请先运行：cd web && npm install")
        return 1

    os.chdir(ROOT)
    try:
        from backend.app.database import init_db, session_scope
        from backend.app.services.demo_data import seed_demo_data

        init_db()
        with session_scope() as session:
            seed_demo_data(session)
    except ImportError as exc:
        print(f"缺少 Python 依赖：{exc}\n请先运行：pip install -r requirements.txt")
        return 1

    host = os.getenv("CROSSPROFIT_HOST", "127.0.0.1")
    api_port = os.getenv("CROSSPROFIT_API_PORT", "8000")
    web_port = os.getenv("CROSSPROFIT_WEB_PORT") or os.getenv("PORT") or "3000"
    env = os.environ.copy()
    env.setdefault("CROSSPROFIT_INTERNAL_API_URL", f"http://{host}:{api_port}")
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", host, "--port", api_port], cwd=ROOT, env=env)
    web_mode = env.get("CROSSPROFIT_WEB_MODE", "development").lower()
    if web_mode in {"production", "prod"}:
        if not (WEB / ".next" / "BUILD_ID").exists():
            print("首次启动：正在构建比赛界面……")
            build = subprocess.run([npm, "run", "build"], cwd=WEB, env=env, check=False)
            if build.returncode:
                api.terminate()
                return build.returncode
        web_command = [npm, "run", "start", "--", "--hostname", host, "--port", web_port]
    else:
        web_command = [npm, "run", "dev", "--", "--hostname", host, "--port", web_port]
    web = subprocess.Popen(web_command, cwd=WEB, env=env)
    print(f"\nCrossProfit AI 比赛界面：http://{host}:{web_port}")
    print(f"FastAPI 文档：http://{host}:{api_port}/docs")
    print("按 Ctrl+C 同时停止两个服务。\n")
    try:
        while api.poll() is None and web.poll() is None:
            time.sleep(0.5)
        return api.returncode or web.returncode or 1
    except KeyboardInterrupt:
        return 0
    finally:
        for process in (web, api):
            if process.poll() is None:
                process.terminate()
        for process in (web, api):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
