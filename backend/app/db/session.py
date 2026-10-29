"""Engine and session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def build_engine(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Create an engine with sane defaults for the configured database."""
    url = database_url or get_settings().database_url
    kwargs: dict[str, object] = {"future": True, "echo": echo}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Recycle stale connections so a restarted Docker container recovers.
        kwargs.update({"pool_pre_ping": True, "pool_recycle": 1800})
    return create_engine(url, **kwargs)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
