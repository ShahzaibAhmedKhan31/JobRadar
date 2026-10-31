"""Startup schema guard and the "database is older than the code" handler."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import ProgrammingError

from app.core.config import Settings
from app.db import schema_check
from app.db.schema_check import SchemaState, ensure_schema, schema_status


class FakeDiagnostic:
    def __init__(self, column_name: str | None = None, table_name: str | None = None):
        self.column_name = column_name
        self.table_name = table_name


class FakeOrig(Exception):
    """Mimics psycopg's error with SQLSTATE and a diagnostic object."""

    def __init__(self, sqlstate: str, *, column: str | None = None):
        super().__init__("boom")
        self.sqlstate = sqlstate
        self.diag = FakeDiagnostic(column_name=column)


def programming_error(sqlstate: str, *, column: str | None = None) -> ProgrammingError:
    return ProgrammingError("SELECT 1", {}, FakeOrig(sqlstate, column=column))


def settings_with(**overrides: Any) -> Settings:
    base = {"schema_check_on_startup": True, "schema_auto_upgrade": False}
    base.update(overrides)
    return Settings(**base)


# ------------------------------------------------------------------ status


def test_status_reports_head(monkeypatch):
    monkeypatch.setattr(schema_check, "head_revision", lambda: "abc123")
    monkeypatch.setattr(schema_check, "current_revision", lambda engine: ("abc123", True))
    status = schema_status(object())
    assert status.state is SchemaState.AT_HEAD
    assert "at head" in status.describe()


def test_status_reports_stale_database(monkeypatch):
    monkeypatch.setattr(schema_check, "head_revision", lambda: "new456")
    monkeypatch.setattr(schema_check, "current_revision", lambda engine: ("old123", True))
    status = schema_status(object())
    assert status.state is SchemaState.STALE
    assert status.is_stale is True
    description = status.describe()
    assert "old123" in description and "new456" in description
    assert "alembic upgrade head" in description


def test_status_without_alembic_table_is_uninitialized(monkeypatch):
    monkeypatch.setattr(schema_check, "head_revision", lambda: "abc123")
    monkeypatch.setattr(schema_check, "current_revision", lambda engine: (None, False))
    status = schema_status(object())
    assert status.state is SchemaState.UNINITIALIZED
    assert "migrations have not been applied" in status.describe()


# ------------------------------------------------------------ ensure_schema


def test_ensure_schema_refuses_to_start_on_a_stale_database(monkeypatch):
    monkeypatch.setattr(
        schema_check,
        "schema_status",
        lambda engine: schema_check.SchemaStatus(
            SchemaState.STALE, current="old123", head="new456"
        ),
    )
    with pytest.raises(RuntimeError) as excinfo:
        ensure_schema(object(), settings_with())
    message = str(excinfo.value)
    assert "alembic upgrade head" in message
    assert "SCHEMA_AUTO_UPGRADE" in message


def test_ensure_schema_can_auto_upgrade(monkeypatch):
    calls: list[str] = []
    statuses = [
        schema_check.SchemaStatus(SchemaState.STALE, current="old123", head="new456"),
        schema_check.SchemaStatus(SchemaState.AT_HEAD, current="new456", head="new456"),
    ]
    monkeypatch.setattr(schema_check, "schema_status", lambda engine: statuses.pop(0))
    monkeypatch.setattr(schema_check, "upgrade_to_head", lambda: calls.append("upgrade"))

    status = ensure_schema(object(), settings_with(schema_auto_upgrade=True))
    assert calls == ["upgrade"]
    assert status.state is SchemaState.AT_HEAD


def test_ensure_schema_is_skipped_when_disabled(monkeypatch):
    def explode(engine):  # pragma: no cover - must not run
        raise AssertionError("schema check should not run")

    monkeypatch.setattr(schema_check, "schema_status", explode)
    status = ensure_schema(object(), settings_with(schema_check_on_startup=False))
    assert status.state is SchemaState.UNKNOWN


def test_ensure_schema_skips_sqlite(monkeypatch):
    def explode(engine):  # pragma: no cover - must not run
        raise AssertionError("schema check should not run on SQLite")

    monkeypatch.setattr(schema_check, "schema_status", explode)
    status = ensure_schema(object(), Settings(database_url="sqlite+pysqlite:///tmp/x.db"))
    assert status.state is SchemaState.UNKNOWN


def test_head_revision_matches_the_migration_files():
    head = schema_check.head_revision()
    assert head and len(head) == 12


# ------------------------------------------------------- error translation


def test_missing_column_becomes_503_with_the_upgrade_command():
    from app.main import schema_error_payload

    status_code, body = schema_error_payload(
        programming_error("42703", column="published_at_is_date_only")
    )
    assert status_code == 503
    assert body["code"] == "schema_out_of_date"
    assert "published_at_is_date_only" in body["detail"]
    assert "alembic upgrade head" in body["detail"]


def test_missing_table_is_reported_too():
    from app.main import schema_error_payload

    status_code, body = schema_error_payload(programming_error("42P01"))
    assert status_code == 503
    assert "table" in body["detail"]


def test_unrelated_programming_error_stays_a_500():
    from app.main import schema_error_payload

    status_code, body = schema_error_payload(programming_error("42601"))  # syntax_error
    assert status_code == 500
    assert body["code"] == "database_error"


def test_endpoint_reports_schema_drift_as_503(client, monkeypatch):
    """A stale database must answer with the fix, not an opaque 500."""
    from app.services import dashboard as dashboard_service

    def boom(*args: Any, **kwargs: Any):
        raise programming_error("42703", column="published_at_is_date_only")

    monkeypatch.setattr(dashboard_service, "get_summary", boom)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "schema_out_of_date"
    assert "alembic upgrade head" in payload["detail"]
