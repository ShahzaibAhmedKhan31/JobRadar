"""Registry configuration and API edge cases."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.core.time import utcnow
from app.services.search_settings import schedule_config
from app.sources.registry import build_registry
from tests.factories import make_application, make_fetch_run, make_job


def test_registry_enabled_sources_allow_list():
    settings = get_settings().model_copy(update={"enabled_sources": ["fixtures"]})
    registry = build_registry(settings)
    assert [adapter.key for adapter in registry.enabled(settings.enabled_sources)] == [
        "fixtures"
    ]
    assert [adapter.key for adapter in registry.refresh_targets(None, settings.enabled_sources)] == [
        "fixtures"
    ]


def test_registry_rejects_unknown_enabled_source():
    settings = get_settings().model_copy(update={"enabled_sources": ["monster"]})
    with pytest.raises(BadRequestError):
        build_registry(settings)


def test_registry_refresh_targets_explicit_unavailable_source():
    registry = build_registry(get_settings())
    targets = registry.refresh_targets(["linkedin", "fixtures"])
    assert [adapter.key for adapter in targets] == ["linkedin", "fixtures"]
    assert registry.get("linkedin") is not None
    assert registry.get("linkedin").can_refresh is False


def test_refresh_history_filters(client, db):
    make_fetch_run(db, source="fixtures", status="success")
    make_fetch_run(db, source="fixtures", status="failed", error_message="boom")
    make_fetch_run(db, source="manual_import", status="skipped")

    failed = client.get("/api/jobs/refresh-history", params={"status": "failed"}).json()
    assert failed["total"] == 1
    assert failed["items"][0]["error_message"] == "boom"

    by_source = client.get(
        "/api/jobs/refresh-history", params={"source": "manual_import"}
    ).json()
    assert by_source["total"] == 1
    assert by_source["items"][0]["status"] == "skipped"


def test_application_notes_can_be_cleared(client, db):
    job = make_job(db)
    application = make_application(db, job, notes="Initial note")
    response = client.patch(
        f"/api/applications/{application.id}", json={"notes": None}
    )
    assert response.status_code == 200
    assert response.json()["notes"] is None


def test_search_settings_scheduler_defaults_from_env(monkeypatch, client):
    monkeypatch.setenv("SCHEDULED_REFRESH_ENABLED", "true")
    monkeypatch.setenv("SCHEDULED_REFRESH_INTERVAL_MINUTES", "120")
    from app.core.config import Settings

    settings = Settings()
    assert settings.scheduled_refresh_enabled is True
    assert settings.scheduled_refresh_interval_minutes == 120

    settings_row = client.get("/api/settings").json()
    # The stored row was created during earlier requests with default values.
    assert settings_row["scheduled_refresh_enabled"] is False


def test_schedule_config_reads_persisted_row(client, db):
    client.put(
        "/api/settings",
        json={"scheduled_refresh_enabled": True, "scheduled_refresh_interval_minutes": 240},
    )
    enabled, interval = schedule_config(db)
    assert enabled is True
    assert interval == 240


def test_health_reports_database(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "time" in body


def test_shortlist_priority_filter_rejects_invalid_value(client):
    response = client.get("/api/shortlist", params={"priority": "urgent"})
    assert response.status_code == 422


def test_application_date_filter_ignores_records_without_date(client, db):
    job = make_job(db)
    make_application(db, job, status="saved")
    today = utcnow().date().isoformat()
    response = client.get(
        "/api/applications", params={"date_from": today, "date_to": today}
    ).json()
    assert response["total"] == 0
