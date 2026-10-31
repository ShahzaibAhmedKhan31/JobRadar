"""Location matching, stored-data facets and sample-data isolation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.time import utcnow
from app.services.jobs import JobFilters, list_jobs
from tests.factories import make_job


def _day_ago() -> datetime:
    today = utcnow().date() - timedelta(days=1)
    return datetime(today.year, today.month, today.day, tzinfo=UTC)


def _seed_mixed(db) -> dict[str, object]:
    """Rows shaped like a real LinkedIn "Karachi, Pakistan" search."""
    return {
        "karachi": make_job(
            db, source="linkedin", title="Senior Software Engineer",
            location="Karachi, Sindh, Pakistan", published_at=_day_ago(),
            published_at_is_date_only=True,
        ),
        "division": make_job(
            db, source="linkedin", title="AI Engineer",
            location="Karachi Division, Sindh, Pakistan", published_at=_day_ago(),
            published_at_is_date_only=True,
        ),
        "country": make_job(
            db, source="linkedin", title="Cloud Engineer", location="Pakistan",
            published_at=_day_ago(), published_at_is_date_only=True,
        ),
        "uae": make_job(
            db, source="linkedin", title="Software Engineer",
            location="Dubai, United Arab Emirates", published_at=_day_ago(),
            published_at_is_date_only=True,
        ),
        "remote": make_job(
            db, source="linkedin", title="Backend Engineer", location="Remote",
            work_arrangement="remote", published_at=_day_ago(),
            published_at_is_date_only=True,
        ),
    }


def test_location_token_matching_handles_real_provider_strings(db):
    rows = _seed_mixed(db)
    result = list_jobs(db, JobFilters(location="Karachi", include_test_data=False))
    ids = {job.id for job in result.jobs}
    assert rows["karachi"].id in ids
    assert rows["division"].id in ids
    assert rows["uae"].id not in ids


def test_location_with_country_still_matches(db):
    """"Karachi, Pakistan" must match "Karachi, Sindh, Pakistan"."""
    rows = _seed_mixed(db)
    result = list_jobs(db, JobFilters(location="Karachi, Pakistan", include_test_data=False))
    ids = {job.id for job in result.jobs}
    assert rows["karachi"].id in ids
    assert rows["division"].id in ids
    assert rows["country"].id not in ids  # country only, no city
    assert rows["uae"].id not in ids


def test_remote_filter_matches_remote_arrangement(db):
    rows = _seed_mixed(db)
    result = list_jobs(db, JobFilters(location="remote", include_test_data=False))
    assert {job.id for job in result.jobs} == {rows["remote"].id}


def test_titles_filter_matches_substring(db):
    rows = _seed_mixed(db)
    result = list_jobs(
        db, JobFilters(titles=["Software Engineer"], include_test_data=False)
    )
    assert {job.id for job in result.jobs} == {rows["karachi"].id, rows["uae"].id}


def test_sample_rows_are_hidden_unless_requested(db):
    make_job(db, source="fixtures", is_test_data=True)
    make_job(db, source="linkedin")
    assert list_jobs(db, JobFilters(include_test_data=False)).total == 1
    assert list_jobs(db, JobFilters(include_test_data=True)).total == 2


def test_facets_explain_what_is_stored(client, db):
    _seed_mixed(db)
    make_job(db, source="fixtures", is_test_data=True)

    payload = client.get("/api/jobs/facets").json()
    assert payload["total"] == 6
    assert payload["real_total"] == 5
    assert payload["sample_total"] == 1
    assert payload["include_test_data"] is False
    locations = {item["value"]: item["count"] for item in payload["locations"]}
    assert "Karachi, Sindh, Pakistan" in locations
    assert "fixtures" not in {item["value"] for item in payload["sources"]}
    companies = {item["value"] for item in payload["companies"]}
    assert companies


def test_facets_can_include_samples_and_scope_by_source(client, db):
    _seed_mixed(db)
    make_job(db, source="fixtures", is_test_data=True)

    with_samples = client.get(
        "/api/jobs/facets", params={"include_test_data": True}
    ).json()
    assert with_samples["total"] == 6
    sources = {item["value"] for item in with_samples["sources"]}
    assert sources == {"linkedin", "fixtures"}

    scoped = client.get("/api/jobs/facets", params={"sources": ["fixtures"]}).json()
    assert scoped["total"] == 1


def test_refresh_all_does_not_load_sample_data(client):
    # Scraping is disabled in tests, so "refresh everything" has no real target:
    # it must report that instead of quietly importing the sample feed.
    response = client.post("/api/jobs/refresh", json={})
    assert response.status_code == 400
    assert "sample" not in response.json()["detail"].lower()
    assert client.get("/api/jobs", params={"include_test_data": True}).json()["total"] == 0


def test_sample_feed_stays_available_when_requested_explicitly(client):
    payload = client.post("/api/jobs/refresh", json={"sources": ["fixtures"]}).json()
    assert payload["new_jobs"] == 26
    assert client.get("/api/jobs").json()["total"] == 0
    assert (
        client.get("/api/jobs", params={"include_test_data": True}).json()["total"] == 26
    )
