"""Removing stored listings that the user never acted on.

A scraper can leave unrelated rows behind (a US-wide feed fetched before a
location was configured, for instance). The cleanup must be able to delete those
without ever touching a listing that was shortlisted or applied to.
"""

from __future__ import annotations

from app.models.job import Job
from app.services.jobs import prune_jobs
from tests.factories import make_application, make_job, make_shortlist


def test_prune_keeps_shortlisted_and_applied_listings(db):
    shortlisted = make_job(db, title="Shortlisted role")
    make_shortlist(db, shortlisted)
    applied = make_job(db, title="Applied role")
    make_application(db, applied)
    for index in range(3):
        make_job(db, title=f"Irrelevant {index}")

    result = prune_jobs(db)

    assert (result.deleted, result.protected, result.matched) == (3, 2, 5)
    remaining = {job.id for job in db.query(Job).all()}
    assert remaining == {shortlisted.id, applied.id}


def test_prune_can_be_limited_to_one_source(db):
    make_job(db, source="linkedin", title="Scraped")
    make_job(db, source="linkedin", title="Also scraped")
    imported = make_job(db, source="manual_import", title="Imported by hand")

    result = prune_jobs(db, sources=["linkedin"])

    assert result.deleted == 2
    assert [job.id for job in db.query(Job).all()] == [imported.id]


def test_prune_leaves_sample_rows_alone_unless_asked(db):
    sample = make_job(db, is_test_data=True, title="Sample")
    real = make_job(db, title="Real")

    assert prune_jobs(db).deleted == 1
    assert [job.id for job in db.query(Job).all()] == [sample.id]

    assert prune_jobs(db, include_test_data=True).deleted == 1
    assert db.query(Job).count() == 0
    assert real.id != sample.id


def test_prune_api_reports_what_it_did(client, db):
    make_job(db, title="One")
    make_job(db, title="Two")
    tracked = make_job(db, title="Tracked")
    make_shortlist(db, tracked)

    payload = client.post("/api/jobs/prune", json={}).json()

    assert payload["deleted"] == 2
    assert payload["protected"] == 1
    assert "Removed 2" in payload["message"]
    assert "shortlisted" in payload["message"]


def test_prune_api_rejects_unknown_sources(client, db):
    make_job(db)
    response = client.post("/api/jobs/prune", json={"sources": ["monster"]})
    assert response.status_code == 422
    assert db.query(Job).count() == 1


def test_prune_api_is_a_no_op_when_there_is_nothing_to_remove(client, db):
    tracked = make_job(db)
    make_application(db, tracked)

    payload = client.post("/api/jobs/prune", json={}).json()

    assert payload["deleted"] == 0
    assert "Nothing removed" in payload["message"]
    assert db.query(Job).count() == 1
