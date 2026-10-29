"""Pytest fixtures.

Safety: tests only ever touch a database whose name ends in ``_test``. The
overridden ``DATABASE_URL`` is validated before any schema is dropped.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterator

import pytest

DEFAULT_TEST_URL = "postgresql+psycopg://jobradar:jobradar@localhost:5432/jobradar_test"


def _database_name(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def _sqlite_url() -> str:
    directory = tempfile.mkdtemp(prefix="jobradar-tests-")
    return f"sqlite+pysqlite:///{directory}/jobradar_test.db"


def _resolve_test_database_url() -> tuple[str, bool]:
    """Prefer PostgreSQL, fall back to a throwaway SQLite file.

    PostgreSQL is the production target; SQLite keeps the suite runnable on
    machines without Docker while still exercising the same SQLAlchemy models.
    """
    candidate = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_URL)
    if _database_name(candidate) == "jobradar_test" or _database_name(candidate).endswith(
        "_test"
    ):
        pass
    else:  # pragma: no cover - configuration guard
        raise RuntimeError(
            "TEST_DATABASE_URL must point at a database whose name ends with '_test'"
        )

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(candidate, connect_args={"connect_timeout": 3})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return candidate, True
    except Exception:
        return _sqlite_url(), False


TEST_DATABASE_URL, POSTGRES_AVAILABLE = _resolve_test_database_url()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("DB_WAIT_ON_STARTUP", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402  (register tables before metadata use)
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def schema_engine() -> Iterator[Engine]:
    assert _database_name(TEST_DATABASE_URL).endswith("_test"), (
        "Refusing to run tests against a non-test database"
    )
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(schema_engine: Engine) -> Iterator[Session]:
    """Session wrapped in an outer transaction that is rolled back per test."""
    connection = schema_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        # Each HTTP request gets a clean view, mirroring the per-request session
        # used in production while still sharing the test transaction.
        db.expire_all()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def registry():
    from app.core.config import get_settings
    from app.sources.registry import build_registry

    return build_registry(get_settings())


@pytest.fixture()
def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]
