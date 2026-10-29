"""Manual import endpoint (authorized path for LinkedIn/Indeed links)."""

from __future__ import annotations

from datetime import timedelta

from app.core.time import utcnow


def _payload(**overrides):
    payload = {
        "title": "Senior Backend Engineer",
        "company_name": "Northwind Analytics",
        "job_url": "https://www.linkedin.com/jobs/view/1234567890",
        "source": "linkedin",
        "location": "Karachi, Pakistan",
        "work_arrangement": "hybrid",
        "experience_level": "mid_senior",
        "description": "Python services, FastAPI and PostgreSQL.",
    }
    payload.update(overrides)
    return payload


def test_manual_import_creates_real_job(client):
    response = client.post("/api/jobs/import", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    job = body["job"]
    assert job["source"] == "linkedin"
    assert job["source_label"] == "LinkedIn"
    assert job["is_test_data"] is False
    assert job["published_at"] is None
    assert job["posting_age_hours"] is None
    assert job["description"].startswith("Python services")
    assert job["possible_duplicates"] == []

    # Jobs created manually are included in normal metrics.
    summary = client.get("/api/dashboard/summary").json()
    assert summary["total_jobs"] == 1


def test_manual_import_deduplicates(client):
    first = client.post("/api/jobs/import", json=_payload()).json()
    second = client.post(
        "/api/jobs/import",
        json=_payload(title="Senior Backend Engineer (reposted)"),
    )
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["job"]["id"] == first["job"]["id"]
    assert client.get("/api/jobs").json()["total"] == 1


def test_manual_import_flags_possible_cross_source_duplicates(client):
    first = client.post("/api/jobs/import", json=_payload()).json()
    second = client.post(
        "/api/jobs/import",
        json=_payload(
            source="indeed",
            job_url="https://pk.indeed.com/viewjob?jk=abcdef",
        ),
    ).json()
    assert second["created"] is True
    assert second["job"]["id"] != first["job"]["id"]
    detail = client.get(f"/api/jobs/{second['job']['id']}").json()
    assert detail["possible_duplicate_count"] == 1
    assert detail["possible_duplicates"][0]["source"] == "linkedin"

    # Both records keep their source-specific URLs.
    listing = client.get("/api/jobs").json()
    urls = {item["job_url"] for item in listing["items"]}
    assert len(urls) == 2


def test_manual_import_accepts_iso_date_and_normalizes_url(client):
    response = client.post(
        "/api/jobs/import",
        json=_payload(
            published_at="2026-10-20T09:00:00Z",
            job_url="HTTPS://Jobs.Example.com/role/?utm_source=newsletter#apply",
        ),
    )
    assert response.status_code == 201
    job = response.json()["job"]
    assert job["job_url"] == "https://jobs.example.com/role"
    assert job["published_at"] is not None
    assert job["posting_age_hours"] is not None


def test_manual_import_validation(client):
    assert client.post("/api/jobs/import", json=_payload(title="  ")).status_code == 422
    assert (
        client.post("/api/jobs/import", json=_payload(job_url="notaurl")).status_code
        == 422
    )
    assert (
        client.post(
            "/api/jobs/import", json=_payload(job_url="javascript:alert(1)")
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/jobs/import",
            json=_payload(
                published_at=(utcnow() + timedelta(days=2)).isoformat()
            ),
        ).status_code
        == 422
    )
    assert (
        client.post("/api/jobs/import", json=_payload(source="greenhouse")).status_code
        == 400
    )
    assert (
        client.post(
            "/api/jobs/import", json=_payload(description="x" * 20001)
        ).status_code
        == 422
    )


def test_manual_import_with_source_job_id_dedupes_per_source(client):
    url = "https://pk.indeed.com/viewjob?jk=stable-1"
    first = client.post(
        "/api/jobs/import",
        json=_payload(source="indeed", job_url=url, source_job_id="stable-1"),
    ).json()
    second = client.post(
        "/api/jobs/import",
        json=_payload(
            source="indeed",
            job_url="https://pk.indeed.com/viewjob?jk=stable-1&from=feed",
            source_job_id="stable-1",
        ),
    ).json()
    assert second["created"] is False
    assert second["job"]["id"] == first["job"]["id"]
