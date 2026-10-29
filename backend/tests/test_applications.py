"""Application tracker API behaviour."""

from __future__ import annotations

from datetime import timedelta

from app.core.constants import ApplicationStatus
from app.core.time import utcnow
from tests.factories import make_application, make_job


def test_create_application_defaults_and_status_change(client, db):
    job = make_job(db, title="Backend Engineer", company_name="Acme")
    created = client.post(
        "/api/applications",
        json={"job_id": str(job.id), "status": "applied", "notes": "Referred by Sam"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "applied"
    assert payload["application_date"] == utcnow().date().isoformat()
    assert payload["job"]["title"] == "Backend Engineer"
    assert payload["resume_reference"] is None

    application_id = payload["id"]
    updated = client.patch(
        f"/api/applications/{application_id}",
        json={
            "status": "interview",
            "follow_up_date": (utcnow().date() + timedelta(days=3)).isoformat(),
            "resume_reference": "resume-backend-v3.pdf",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "interview"
    assert updated.json()["resume_reference"] == "resume-backend-v3.pdf"

    jobs = client.get("/api/jobs").json()
    assert jobs["items"][0]["application"]["status"] == "interview"


def test_duplicate_application_is_rejected(client, db):
    job = make_job(db)
    first = client.post("/api/applications", json={"job_id": str(job.id)})
    assert first.status_code == 201
    second = client.post("/api/applications", json={"job_id": str(job.id)})
    assert second.status_code == 409
    assert "already has a tracking record" in second.json()["detail"]


def test_application_for_missing_job(client):
    response = client.post(
        "/api/applications",
        json={"job_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404


def test_saved_record_gets_date_when_marked_applied(client, db):
    job = make_job(db)
    created = client.post(
        "/api/applications",
        json={"job_id": str(job.id), "status": "saved"},
    ).json()
    assert created["application_date"] is None

    applied = client.patch(
        f"/api/applications/{created['id']}", json={"status": "applied"}
    ).json()
    assert applied["application_date"] == utcnow().date().isoformat()


def test_application_date_validation(client, db):
    job = make_job(db)
    future = (utcnow().date() + timedelta(days=5)).isoformat()
    invalid = client.post(
        "/api/applications",
        json={"job_id": str(job.id), "status": "applied", "application_date": future},
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/applications",
        json={"job_id": str(job.id), "status": "applied"},
    ).json()
    applied_today = utcnow().date().isoformat()
    follow_up = (utcnow().date() - timedelta(days=1)).isoformat()
    malformed = client.patch(
        f"/api/applications/{created['id']}",
        json={"application_date": applied_today, "follow_up_date": follow_up},
    )
    assert malformed.status_code == 422

    unknown_field = client.patch(
        f"/api/applications/{created['id']}", json={"score": 10}
    )
    assert unknown_field.status_code == 422


def test_application_list_and_filters(client, db):
    now = utcnow()
    acme = make_job(db, company_name="Acme Analytics", title="Backend Engineer")
    orbit = make_job(db, company_name="Orbit Freight", title="Data Engineer")
    kite = make_job(db, company_name="Kite Commerce", title="Product Manager")

    make_application(
        db, acme, status=ApplicationStatus.APPLIED,
        application_date=now.date() - timedelta(days=1),
    )
    make_application(
        db, orbit, status=ApplicationStatus.INTERVIEW,
        application_date=now.date() - timedelta(days=4), notes="Tech round scheduled",
    )
    make_application(db, kite, status=ApplicationStatus.SAVED)

    listing = client.get("/api/applications", params={"page_size": 50}).json()
    assert listing["total"] == 3
    statuses = {item["status"] for item in listing["items"]}
    assert statuses == {"applied", "interview", "saved"}

    interviews = client.get("/api/applications", params={"status": "interview"}).json()
    assert interviews["total"] == 1
    assert interviews["items"][0]["job"]["company_name"] == "Orbit Freight"

    multiple = client.get(
        "/api/applications", params=[("status", "applied"), ("status", "saved")]
    ).json()
    assert multiple["total"] == 2

    by_company = client.get("/api/applications", params={"company": "orbit"}).json()
    assert by_company["total"] == 1

    by_search = client.get("/api/applications", params={"search": "Tech round"}).json()
    assert by_search["total"] == 1

    by_date = client.get(
        "/api/applications",
        params={
            "date_from": (now.date() - timedelta(days=2)).isoformat(),
            "date_to": now.date().isoformat(),
        },
    ).json()
    assert by_date["total"] == 1
    assert by_date["items"][0]["job"]["company_name"] == "Acme Analytics"

    oldest = client.get("/api/applications", params={"sort": "oldest"}).json()
    assert oldest["items"][-1]["job"]["company_name"] == "Kite Commerce"


def test_get_and_delete_application(client, db):
    job = make_job(db)
    application = make_application(db, job, status=ApplicationStatus.OFFER)

    detail = client.get(f"/api/applications/{application.id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "offer"

    deleted = client.delete(f"/api/applications/{application.id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/applications/{application.id}").status_code == 404
    assert client.delete(f"/api/applications/{application.id}").status_code == 404


def test_all_statuses_supported(client, db):
    statuses = ["saved", "applied", "assessment", "interview", "offer", "rejected", "withdrawn"]
    for index, status in enumerate(statuses):
        job = make_job(db, source_job_id=f"status-{index}", job_url=f"https://jobs.example.com/status-{index}")
        created = client.post(
            "/api/applications", json={"job_id": str(job.id), "status": status}
        )
        assert created.status_code == 201, created.text
        assert created.json()["status"] == status
    assert client.get("/api/applications", params={"page_size": 50}).json()["total"] == 7


def test_database_prevents_duplicate_application_rows(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.models.application import Application

    job = make_job(db)
    make_application(db, job)
    duplicate = Application(job_id=job.id, status=ApplicationStatus.APPLIED)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(duplicate)
        db.flush()
