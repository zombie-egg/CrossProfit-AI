from __future__ import annotations

from contextlib import contextmanager
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base


def build_engine(url: str | None = None):
    db_url = url or settings.database_url
    return create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    # create_all is idempotent, but two first-start processes can race between
    # SQLite's table-existence check and CREATE TABLE. Retry that narrow case.
    for attempt in range(4):
        try:
            Base.metadata.create_all(engine)
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
