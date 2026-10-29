"""Dashboard endpoints must reflect stored data exactly."""

from __future__ import annotations

from datetime import timedelta

from app.core.constants import ApplicationStatus
from app.core.time import utcnow
from tests.factories import make_application, make_fetch_run, make_job, make_shortlist


def _seed(db):
    now = utcnow()
    fresh = make_job(
        db,
        title="Backend Engineer",
        company_name="Acme",
        published_at=now - timedelta(hours=3),
        first_seen_at=now - timedelta(hours=2),
        source="linkedin",
        source_job_id="dash-1",
    )
    older = make_job(
        db,
        title="Data Engineer",
        company_name="Orbit",
        published_at=now - timedelta(hours=50),
        first_seen_at=now - timedelta(hours=40),
        source="indeed",
        source_job_id="dash-2",
    )
    test_row = make_job(
        db,
        title="Sample role",
        company_name="Sample Co",
        published_at=now - timedelta(hours=1),
        first_seen_at=now - timedelta(hours=1),
        is_test_data=True,
        source="fixtures",
        source_job_id="dash-3",
    )
    make_shortlist(db, fresh)
    make_application(db, fresh, status=ApplicationStatus.INTERVIEW)
    make_application(
        db, older, status=ApplicationStatus.OFFER,
        follow_up_date=now.date() + timedelta(days=2),
    )
    return fresh, older, test_row


def test_dashboard_metrics_reflect_database(client, db):
    _seed(db)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    # Test data excluded by default.
    assert data["total_jobs"] == 2
    assert data["test_data_jobs"] == 1
    assert data["shortlisted_jobs"] == 1
    assert data["applications_total"] == 2
    assert data["applications_submitted"] == 2
    assert data["applications_in_progress"] == 1
    assert data["interviews"] == 1
    assert data["offers"] == 1
    assert data["jobs_discovered_recent"] == 1  # only `fresh` in the last 24h
    assert data["jobs_published_recent"] == 1
    assert data["upcoming_follow_ups"] == 1
    assert data["include_test_data"] is False

    breakdown = {item["status"]: item["count"] for item in data["status_breakdown"]}
    assert breakdown["interview"] == 1
    assert breakdown["offer"] == 1
    assert breakdown["saved"] == 0
    assert len(data["status_breakdown"]) == 7

    sources = {item["source"]: item["count"] for item in data["source_breakdown"]}
    assert sources == {"indeed": 1, "linkedin": 1}

    recent_titles = [item["title"] for item in data["recent_jobs"]]
    assert recent_titles[0] == "Backend Engineer"
    assert data["latest_refresh"] is None


def test_dashboard_recent_period_and_test_data_switch(client, db):
    _seed(db)
    wide = client.get(
        "/api/dashboard/summary", params={"recent_period_hours": 72}
    ).json()
    assert wide["jobs_discovered_recent"] == 2

    with_test = client.get(
        "/api/dashboard/summary", params={"include_test_data": True}
    ).json()
    assert with_test["total_jobs"] == 3
    assert with_test["include_test_data"] is True
    assert with_test["test_data_jobs"] == 1


def test_dashboard_empty_state(client):
    data = client.get("/api/dashboard/summary").json()
    assert data["total_jobs"] == 0
    assert data["shortlisted_jobs"] == 0
    assert data["applications_total"] == 0
    assert all(item["count"] == 0 for item in data["status_breakdown"])
    assert data["recent_jobs"] == []
    assert data["latest_refresh"] is None


def test_dashboard_surfaces_latest_refresh(client, db):
    make_fetch_run(db, source="fixtures", new_jobs_count=5, fetched_jobs_count=5)
    data = client.get("/api/dashboard/summary").json()
    assert data["latest_refresh"]["source"] == "fixtures"
    assert data["latest_refresh"]["new_jobs_count"] == 5


def test_activity_series(client, db):
    now = utcnow()
    make_job(db, first_seen_at=now - timedelta(hours=1), published_at=now - timedelta(hours=2))
    make_job(
        db,
        first_seen_at=now - timedelta(days=2),
        published_at=now - timedelta(days=2),
        source_job_id="activity-2",
    )
    job = make_job(db, source_job_id="activity-3")
    make_application(db, job, status=ApplicationStatus.APPLIED)
    saved_job = make_job(db, source_job_id="activity-4")
    make_application(db, saved_job, status=ApplicationStatus.SAVED)

    response = client.get("/api/dashboard/activity", params={"days": 7})
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert len(data["points"]) == 7
    assert data["points"][-1]["date"] == now.date().isoformat()
    assert data["jobs_discovered_total"] == 4
    assert data["applications_submitted_total"] == 1  # `saved` is not a submission
    assert data["points"][-1]["applications_submitted"] == 1


def test_activity_requires_valid_range(client):
    assert client.get("/api/dashboard/activity", params={"days": 0}).status_code == 422
    assert client.get("/api/dashboard/activity", params={"days": 200}).status_code == 422
