import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import init_db, session_scope
from backend.app.services.demo_data import seed_demo_data

init_db()
with session_scope() as session:
    seed_demo_data(session)
print("Demo data ready.")
