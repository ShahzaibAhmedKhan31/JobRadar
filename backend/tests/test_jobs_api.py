"""Job discovery API: filters, sorting, posting age, refresh."""

from __future__ import annotations

from datetime import timedelta

from app.core.constants import ApplicationStatus, ExperienceLevel, WorkArrangement
from app.core.time import utcnow
from app.sources.fixtures import load_fixture_payload
from tests.factories import make_application, make_job, make_shortlist


def _seed_jobs(db):
    now = utcnow()
    backend = make_job(
        db,
        title="Backend Engineer",
        company_name="Acme Analytics",
        location="Karachi, Pakistan",
        work_arrangement=WorkArrangement.HYBRID,
        experience_level=ExperienceLevel.MID_SENIOR,
        description="Python, FastAPI and PostgreSQL services.",
        published_at=now - timedelta(hours=2),
        first_seen_at=now - timedelta(hours=1),
        source="linkedin",
        source_job_id="li-1",
    )
    designer = make_job(
        db,
        title="Product Designer",
        company_name="Tessera Studio",
        location="Berlin, Germany",
        work_arrangement=WorkArrangement.REMOTE,
        experience_level=ExperienceLevel.ASSOCIATE,
        description="Figma design systems for developer tools.",
        published_at=now - timedelta(hours=30),
        first_seen_at=now - timedelta(hours=2),
        source="indeed",
        source_job_id="in-1",
    )
    unknown_date = make_job(
        db,
        title="Data Engineer",
        company_name="Orbit Freight",
        location="Remote (Worldwide)",
        work_arrangement=WorkArrangement.REMOTE,
        experience_level=ExperienceLevel.MID_SENIOR,
        description="Airflow, dbt and PostgreSQL pipelines.",
        published_at=None,
        first_seen_at=now - timedelta(hours=3),
        source="manual_import",
        source_job_id=None,
    )
    old = make_job(
        db,
        title="Engineering Manager",
        company_name="Kite Commerce",
        location="Dubai, United Arab Emirates",
        work_arrangement=WorkArrangement.ONSITE,
        experience_level=ExperienceLevel.MID_SENIOR,
        description="People management for platform teams.",
        published_at=now - timedelta(hours=100),
        first_seen_at=now - timedelta(hours=4),
        source="linkedin",
        source_job_id="li-2",
    )
    test_row = make_job(
        db,
        title="Sample QA Engineer",
        company_name="Sample Co",
        work_arrangement=WorkArrangement.ONSITE,
        experience_level=ExperienceLevel.ENTRY,
        published_at=now - timedelta(hours=1),
        first_seen_at=now,
        is_test_data=True,
        source="fixtures",
        source_job_id="fx-test",
    )
    return backend, designer, unknown_date, old, test_row


def test_empty_database_returns_empty_page(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["unknown_published_count"] == 0


def test_filters_by_work_arrangement_and_source(client, db):
    _seed_jobs(db)
    remote = client.get("/api/jobs", params={"work_arrangement": "remote"}).json()
    assert remote["total"] == 2
    assert {item["title"] for item in remote["items"]} == {
        "Product Designer",
        "Data Engineer",
    }

    linkedin = client.get("/api/jobs", params={"sources": ["linkedin"]}).json()
    assert linkedin["total"] == 2
    assert all(item["source"] == "linkedin" for item in linkedin["items"])


def test_filters_by_title_keywords_and_experience(client, db):
    _seed_jobs(db)
    titles = client.get("/api/jobs", params={"titles": ["Backend"]}).json()
    assert [item["title"] for item in titles["items"]] == ["Backend Engineer"]

    keywords = client.get("/api/jobs", params={"keywords": ["Airflow"]}).json()
    assert [item["title"] for item in keywords["items"]] == ["Data Engineer"]

    entry = client.get(
        "/api/jobs",
        params={"experience_level": "entry", "include_test_data": False},
    ).json()
    assert entry["total"] == 0  # the only entry-level row is test data


def test_location_filter_matches_remote_arrangement(client, db):
    _seed_jobs(db)
    response = client.get("/api/jobs", params={"location": "Remote"}).json()
    titles = {item["title"] for item in response["items"]}
    assert {"Data Engineer", "Product Designer"} <= titles
    assert "Engineering Manager" not in titles


def test_free_text_search(client, db):
    _seed_jobs(db)
    response = client.get("/api/jobs", params={"q": "figma"}).json()
    assert response["total"] == 1
    assert response["items"][0]["company_name"] == "Tessera Studio"


def test_posting_age_uses_published_at_not_first_seen(client, db):
    _seed_jobs(db)
    response = client.get("/api/jobs", params={"max_age_hours": 48}).json()
    titles = {item["title"] for item in response["items"]}
    assert "Backend Engineer" in titles
    assert "Product Designer" in titles
    # Discovered recently but published 100h ago: excluded by posting age.
    assert "Engineering Manager" not in titles
    # Unknown publication time is excluded by default but reported.
    assert "Data Engineer" not in titles
    assert response["unknown_published_count"] == 1


def test_include_unknown_published(client, db):
    _seed_jobs(db)
    response = client.get(
        "/api/jobs",
        params={"max_age_hours": 48, "include_unknown_published": True},
    ).json()
    titles = {item["title"] for item in response["items"]}
    assert "Data Engineer" in titles
    assert "Engineering Manager" not in titles
    data_engineer = next(
        item for item in response["items"] if item["title"] == "Data Engineer"
    )
    assert data_engineer["published_at"] is None
    assert data_engineer["posting_age_hours"] is None


def test_posting_age_exposes_hours(client, db):
    _seed_jobs(db)
    response = client.get("/api/jobs", params={"sources": ["linkedin"]}).json()
    backend = next(item for item in response["items"] if item["title"] == "Backend Engineer")
    assert backend["posting_age_hours"] is not None
    assert 1.5 <= backend["posting_age_hours"] <= 2.5
    assert backend["discovered_age_hours"] >= 0.5


def test_sorting_newest_and_relevant(client, db):
    _seed_jobs(db)
    newest = client.get("/api/jobs", params={"sort": "newest"}).json()
    published = [item["published_at"] for item in newest["items"]]
    known = [value for value in published if value is not None]
    assert known == sorted(known, reverse=True)
    assert published[-1] is None  # jobs without a publication date sort last

    relevant = client.get(
        "/api/jobs", params={"sort": "relevant", "q": "Product Designer"}
    ).json()
    assert relevant["items"][0]["title"] == "Product Designer"


def test_pagination(client, db):
    _seed_jobs(db)
    response = client.get("/api/jobs", params={"page": 2, "page_size": 2}).json()
    assert response["total"] == 5
    assert response["pages"] == 3
    assert len(response["items"]) == 2
    assert response["page"] == 2

    beyond = client.get("/api/jobs", params={"page": 9, "page_size": 2}).json()
    assert beyond["items"] == []
    assert beyond["total"] == 5


def test_shortlisted_and_application_status_filters(client, db):
    backend, designer, _, _, _ = _seed_jobs(db)
    make_shortlist(db, backend)
    make_application(db, designer, status=ApplicationStatus.INTERVIEW)

    shortlisted = client.get("/api/jobs", params={"shortlisted": True}).json()
    assert [item["title"] for item in shortlisted["items"]] == ["Backend Engineer"]
    assert shortlisted["items"][0]["is_shortlisted"] is True

    interviewing = client.get(
        "/api/jobs", params={"application_status": "interview"}
    ).json()
    assert [item["title"] for item in interviewing["items"]] == ["Product Designer"]
    assert interviewing["items"][0]["application"]["status"] == "interview"


def test_test_data_is_filterable(client, db):
    _seed_jobs(db)
    default = client.get("/api/jobs").json()
    assert default["total"] == 5
    clean = client.get("/api/jobs", params={"include_test_data": False}).json()
    assert clean["total"] == 4
    assert all(not item["is_test_data"] for item in clean["items"])


def test_unknown_source_filter_rejected(client):
    response = client.get("/api/jobs", params={"sources": ["monster"]})
    assert response.status_code == 422
    assert "monster" in response.json()["detail"]


def test_job_detail_and_missing_job(client, db):
    backend, _, _, _, _ = _seed_jobs(db)
    response = client.get(f"/api/jobs/{backend.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["description"].startswith("Python, FastAPI")
    assert body["description_snippet"]
    assert body["possible_duplicates"] == []

    missing = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    malformed = client.get("/api/jobs/not-a-uuid")
    assert malformed.status_code == 422


def test_refresh_imports_fixtures_then_is_idempotent(client):
    expected = len(load_fixture_payload()["jobs"])
    first = client.post("/api/jobs/refresh", json={"sources": ["fixtures"]})
    assert first.status_code == 200
    payload = first.json()
    assert payload["new_jobs"] == expected
    assert payload["runs"][0]["status"] == "success"
    assert payload["runs"][0]["new_jobs_count"] == expected

    jobs = client.get("/api/jobs", params={"page_size": 100}).json()
    assert jobs["total"] == expected
    assert all(item["is_test_data"] for item in jobs["items"])

    second = client.post("/api/jobs/refresh", json={"sources": ["fixtures"]})
    second_payload = second.json()
    assert second_payload["new_jobs"] == 0
    assert second_payload["updated_jobs"] == 0
    assert second_payload["runs"][0]["unchanged_jobs_count"] == expected


def test_refresh_reports_unavailable_sources(client):
    response = client.post(
        "/api/jobs/refresh", json={"sources": ["linkedin", "indeed"]}
    )
    assert response.status_code == 200
    runs = response.json()["runs"]
    assert [run["status"] for run in runs] == ["skipped", "skipped"]
    assert all(run["error_message"] for run in runs)
    # The run history must say *why* nothing was imported and how to opt in.
    assert all("JOBSPY" in run["error_message"] for run in runs)


def test_refresh_rejects_unknown_source(client):
    response = client.post("/api/jobs/refresh", json={"sources": ["monster"]})
    assert response.status_code == 400
    assert "monster" in response.json()["detail"]


def test_refresh_honours_limit_and_records_history(client):
    response = client.post(
        "/api/jobs/refresh", json={"sources": ["fixtures"], "limit": 3}
    )
    assert response.json()["new_jobs"] == 3

    history = client.get("/api/jobs/refresh-history").json()
    assert history["total"] == 1
    assert history["items"][0]["source"] == "fixtures"
    assert history["items"][0]["trigger"] == "manual"
    assert history["items"][0]["finished_at"] is not None
    assert history["items"][0]["fetched_jobs_count"] == 3
