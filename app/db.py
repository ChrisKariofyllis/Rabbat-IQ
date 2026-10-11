"""SQLite engine. A process-wide lock keeps writes single-file safe."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

engine = None
SessionLocal: sessionmaker[Session] | None = None
_db_lock = threading.RLock()


def init_db(url: str) -> None:
    global engine, SessionLocal
    if url.startswith("sqlite:///"):
        path = url.removeprefix("sqlite:///")
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    if engine is not None:
        engine.dispose()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized")
    with _db_lock:
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
