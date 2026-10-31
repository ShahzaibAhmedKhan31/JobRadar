"""Search settings, source metadata and health checks."""

from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_root_and_openapi(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["docs"] == "/docs"

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    for expected in [
        "/api/jobs",
        "/api/jobs/refresh",
        "/api/shortlist/{job_id}",
        "/api/applications/{application_id}",
        "/api/dashboard/summary",
        "/api/dashboard/activity",
        "/health",
    ]:
        assert expected in paths


def test_search_settings_defaults_and_update(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    defaults = response.json()
    assert defaults["default_work_arrangement"] == "any"
    assert defaults["default_experience_level"] == "any"
    assert defaults["default_posting_age_hours"] == 168
    assert defaults["default_sources"] == []
    assert defaults["scheduled_refresh_enabled"] is False

    updated = client.put(
        "/api/settings",
        json={
            "default_titles": "Backend Engineer, Data Engineer",
            "default_location": "Karachi",
            "default_work_arrangement": "hybrid",
            "default_posting_age_hours": 48,
            "default_sources": ["linkedin", "indeed"],
            "scheduled_refresh_interval_minutes": 90,
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["default_titles"].startswith("Backend Engineer")
    assert body["default_sources"] == ["linkedin", "indeed"]
    assert body["default_posting_age_hours"] == 48
    assert body["scheduled_refresh_interval_minutes"] == 90

    reread = client.get("/api/settings").json()
    assert reread["default_work_arrangement"] == "hybrid"


def test_search_settings_validation(client):
    unknown_source = client.put(
        "/api/settings", json={"default_sources": ["monster"]}
    )
    assert unknown_source.status_code == 400

    invalid_interval = client.put(
        "/api/settings", json={"scheduled_refresh_interval_minutes": 5}
    )
    assert invalid_interval.status_code == 422

    invalid_arrangement = client.put(
        "/api/settings", json={"default_work_arrangement": "everywhere"}
    )
    assert invalid_arrangement.status_code == 422


def test_sources_metadata(client, db):
    response = client.get("/api/sources")
    assert response.status_code == 200
    sources = {source["key"]: source for source in response.json()["sources"]}

    assert set(sources) == {"linkedin", "indeed", "manual_import", "fixtures"}
    # Scraping is opt-in, so with JOBSPY_ENABLED=false (the test default) the
    # adapters exist but refuse to run and explain how to turn them on.
    assert sources["linkedin"]["availability"] == "not_configured"
    assert sources["linkedin"]["can_refresh"] is False
    assert sources["linkedin"]["supports_refresh"] is True
    assert "JOBSPY_ENABLED" in sources["linkedin"]["availability_reason"]
    assert sources["linkedin"]["required_config"] == ["python-jobspy"]
    assert sources["indeed"]["availability"] == "not_configured"
    assert sources["indeed"]["can_refresh"] is False
    assert sources["fixtures"]["availability"] == "available"
    assert sources["fixtures"]["is_test_data"] is True
    assert sources["manual_import"]["supports_refresh"] is False
    assert all(source["stored_jobs_count"] == 0 for source in sources.values())

    client.post("/api/jobs/refresh", json={"sources": ["fixtures"]})
    sources = {
        source["key"]: source
        for source in client.get("/api/sources").json()["sources"]
    }
    assert sources["fixtures"]["stored_jobs_count"] > 0
    assert sources["fixtures"]["last_run"]["status"] == "success"
