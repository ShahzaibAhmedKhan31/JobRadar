"""Alembic migrations must build the schema from scratch (and roll back)."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "jobs",
    "shortlisted_jobs",
    "applications",
    "job_fetch_runs",
    "search_settings",
}


@pytest.fixture()
def fresh_database_url(tmp_path, monkeypatch) -> str:
    url = f"sqlite+pysqlite:///{tmp_path}/migration_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


def test_upgrade_head_creates_schema(fresh_database_url):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")

    engine = create_engine(fresh_database_url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= EXPECTED_TABLES
    job_columns = {column["name"] for column in inspector.get_columns("jobs")}
    assert {
        "id",
        "source",
        "source_job_id",
        "title",
        "company_name",
        "location",
        "work_arrangement",
        "experience_level",
        "description",
        "job_url",
        "published_at",
        "first_seen_at",
        "last_seen_at",
        "created_at",
        "updated_at",
    } <= job_columns
    index_names = {index["name"] for index in inspector.get_indexes("jobs")}
    assert "uq_jobs_source_source_job_id" in index_names
    assert "uq_jobs_source_external_key" in index_names
    engine.dispose()


def test_downgrade_and_reupgrade(fresh_database_url):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_engine(fresh_database_url)
    tables = set(inspect(engine).get_table_names())
    assert not (EXPECTED_TABLES & tables)
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(fresh_database_url)
    assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES
    engine.dispose()
