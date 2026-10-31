"""Shortlist API: create, update, remove and refresh persistence."""

from __future__ import annotations

from datetime import timedelta

from app.core.constants import Priority
from app.core.time import utcnow
from tests.factories import make_job, make_shortlist


def test_shortlist_create_update_and_remove(client, db):
    job = make_job(db, title="Backend Engineer", company_name="Acme")

    created = client.post(
        f"/api/shortlist/{job.id}",
        json={"priority": "high", "notes": "Strong match for platform team"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["priority"] == "high"
    assert body["notes"] == "Strong match for platform team"
    assert body["job"]["is_shortlisted"] is True

    listed = client.get("/api/shortlist").json()
    assert listed["total"] == 1
    assert listed["items"][0]["job"]["id"] == str(job.id)

    patched = client.patch(
        f"/api/shortlist/{job.id}", json={"notes": "Ask about on-call rotation"}
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Ask about on-call rotation"
    assert patched.json()["priority"] == "high"  # untouched

    patched_priority = client.patch(
        f"/api/shortlist/{job.id}", json={"priority": "low"}
    )
    assert patched_priority.json()["priority"] == "low"

    deleted = client.delete(f"/api/shortlist/{job.id}")
    assert deleted.status_code == 204
    assert client.get("/api/shortlist").json()["total"] == 0

    missing = client.delete(f"/api/shortlist/{job.id}")
    assert missing.status_code == 404


def test_shortlisting_is_idempotent(client, db):
    job = make_job(db)
    first = client.post(f"/api/shortlist/{job.id}", json={"priority": "low"})
    assert first.status_code == 201
    second = client.post(f"/api/shortlist/{job.id}", json={"priority": "medium"})
    assert second.status_code == 200
    assert second.json()["priority"] == "medium"
    assert client.get("/api/shortlist").json()["total"] == 1


def test_shortlist_unknown_job_returns_404(client, db):
    response = client.post(
        "/api/shortlist/00000000-0000-0000-0000-000000000000", json={}
    )
    assert response.status_code == 404
    patch = client.patch(
        "/api/shortlist/00000000-0000-0000-0000-000000000000", json={"notes": "x"}
    )
    assert patch.status_code == 404


def test_shortlist_does_not_create_application(client, db):
    job = make_job(db)
    client.post(f"/api/shortlist/{job.id}", json={"priority": "high"})
    applications = client.get("/api/applications").json()
    assert applications["total"] == 0


def test_shortlist_filters(client, db):
    now = utcnow()
    high = make_job(db, source="linkedin", source_job_id="s-1", title="Platform Engineer")
    low = make_job(db, source="indeed", source_job_id="s-2", title="Data Analyst")
    make_shortlist(db, high, priority=Priority.HIGH, notes="Priority lead")
    make_shortlist(db, low, priority=Priority.LOW)

    by_priority = client.get("/api/shortlist", params={"priority": "high"}).json()
    assert by_priority["total"] == 1
    assert by_priority["items"][0]["job"]["title"] == "Platform Engineer"

    by_source = client.get("/api/shortlist", params={"sources": ["indeed"]}).json()
    assert by_source["total"] == 1
    assert by_source["items"][0]["job"]["source"] == "indeed"

    by_search = client.get("/api/shortlist", params={"search": "Priority lead"}).json()
    assert by_search["total"] == 1

    today = now.date().isoformat()
    by_date = client.get(
        "/api/shortlist", params={"date_from": today, "date_to": today}
    ).json()
    assert by_date["total"] == 2

    future = (now + timedelta(days=3)).date().isoformat()
    assert (
        client.get("/api/shortlist", params={"date_from": future}).json()["total"] == 0
    )

    sorted_by_priority = client.get(
        "/api/shortlist", params={"sort": "priority"}
    ).json()
    assert [entry["priority"] for entry in sorted_by_priority["items"]] == [
        "high",
        "low",
    ]


def test_shortlist_notes_survive_source_refresh(client, db):
    refresh = client.post("/api/jobs/refresh", json={"sources": ["fixtures"]})
    assert refresh.status_code == 200
    jobs = client.get(
        "/api/jobs", params={"page_size": 100, "include_test_data": True}
    ).json()["items"]
    job = jobs[0]

    client.post(
        f"/api/shortlist/{job['id']}",
        json={"priority": "high", "notes": "Follow up with recruiter"},
    )

    client.post("/api/jobs/refresh", json={"sources": ["fixtures"]})
    shortlist = client.get("/api/shortlist").json()
    assert shortlist["total"] == 1
    entry = shortlist["items"][0]
    assert entry["notes"] == "Follow up with recruiter"
    assert entry["priority"] == "high"
    assert entry["job"]["id"] == job["id"]
    assert entry["job"]["first_seen_at"] == job["first_seen_at"]


def test_shortlist_validation(client, db):
    job = make_job(db)
    bad_priority = client.post(f"/api/shortlist/{job.id}", json={"priority": "urgent"})
    assert bad_priority.status_code == 422
    unknown_fields = client.post(
        f"/api/shortlist/{job.id}", json={"priority": "high", "starred": True}
    )
    assert unknown_fields.status_code == 422
