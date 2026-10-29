"""Ingestion, sanitization and deduplication behaviour."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.time import utcnow
from app.core.urls import InvalidJobUrlError, job_fingerprint, validate_job_url
from app.models.job import Job
from app.services.ingestion import (
    InvalidJobPayload,
    ingest_many,
    sanitize_job,
    upsert_job,
)
from tests.factories import make_job, make_normalized


def test_upsert_creates_then_dedupes_on_source_job_id(db):
    item = make_normalized(source_job_id="abc-1")
    first = upsert_job(db, source="linkedin", item=item)
    db.commit()
    assert first.kind == "new"

    second = upsert_job(db, source="linkedin", item=item)
    db.commit()
    assert second.kind == "unchanged"
    assert second.job.id == first.job.id
    assert db.execute(select(func.count()).select_from(Job)).scalar_one() == 1


def test_upsert_updates_changed_fields_and_keeps_first_seen(db):
    item = make_normalized(source_job_id="abc-2", title="Backend Engineer")
    first = upsert_job(db, source="linkedin", item=item)
    db.commit()
    original_first_seen = first.job.first_seen_at

    changed = make_normalized(
        source_job_id="abc-2",
        title="Senior Backend Engineer",
        description="Updated description",
    )
    second = upsert_job(db, source="linkedin", item=changed)
    db.commit()

    assert second.kind == "updated"
    assert second.job.id == first.job.id
    assert second.job.title == "Senior Backend Engineer"
    assert second.job.description == "Updated description"
    assert second.job.first_seen_at == original_first_seen


def test_published_at_is_never_overwritten_or_invented(db):
    known = make_normalized(
        source_job_id="abc-3", published_at=utcnow() - timedelta(hours=10)
    )
    job = upsert_job(db, source="linkedin", item=known).job
    db.commit()
    original_published = job.published_at

    without_date = make_normalized(source_job_id="abc-3", published_at=None)
    upsert_job(db, source="linkedin", item=without_date)
    db.commit()
    db.refresh(job)
    assert job.published_at == original_published

    different_date = make_normalized(
        source_job_id="abc-3", published_at=utcnow() - timedelta(hours=1)
    )
    upsert_job(db, source="linkedin", item=different_date)
    db.commit()
    db.refresh(job)
    assert job.published_at == original_published


def test_missing_publication_timestamp_stays_null(db):
    item = make_normalized(source_job_id="abc-4", published_at=None)
    job = upsert_job(db, source="indeed", item=item).job
    db.commit()
    assert job.published_at is None
    assert job.first_seen_at is not None


def test_dedupes_by_url_when_provider_has_no_id(db):
    first = make_normalized(source_job_id=None)
    second = make_normalized(
        source_job_id=None,
        title=first.title,
        company_name=first.company_name,
        job_url=first.job_url,
    )
    one = upsert_job(db, source="manual_import", item=first)
    two = upsert_job(db, source="manual_import", item=second)
    db.commit()
    assert two.job.id == one.job.id
    assert db.execute(select(func.count()).select_from(Job)).scalar_one() == 1


def test_tracking_parameters_do_not_create_duplicates(db):
    item = make_normalized(
        source_job_id=None, job_url="https://jobs.example.com/acme/backend?utm_source=x"
    )
    same = make_normalized(
        source_job_id=None,
        title=item.title,
        company_name=item.company_name,
        job_url="https://jobs.example.com/acme/backend",
    )
    one = upsert_job(db, source="manual_import", item=item)
    two = upsert_job(db, source="manual_import", item=same)
    db.commit()
    assert one.job.id == two.job.id


def test_same_title_company_on_different_urls_is_not_merged(db):
    first = make_normalized(
        source_job_id="a-1",
        title="Data Engineer",
        company_name="Orbit Freight",
        job_url="https://jobs.example.com/orbit/data-1",
    )
    second = make_normalized(
        source_job_id="a-2",
        title="Data Engineer",
        company_name="Orbit Freight",
        job_url="https://jobs.example.com/orbit/data-2",
    )
    upsert_job(db, source="linkedin", item=first)
    upsert_job(db, source="linkedin", item=second)
    db.commit()
    assert db.execute(select(func.count()).select_from(Job)).scalar_one() == 2


def test_same_listing_on_two_sources_is_kept_per_source(db):
    item = make_normalized(source_job_id="shared-1")
    upsert_job(db, source="linkedin", item=item)
    upsert_job(db, source="indeed", item=item)
    db.commit()
    sources = set(db.execute(select(Job.source)).scalars().all())
    assert sources == {"linkedin", "indeed"}


def test_sanitize_strips_html_and_whitespace():
    item = make_normalized(
        title="  <b>Senior</b>   Backend   Engineer ",
        description="<p>Build <strong>APIs</strong></p><ul><li>Python</li><li>SQL</li></ul>",
    )
    clean = sanitize_job(item)
    assert clean.title == "Senior Backend Engineer"
    assert "<" not in (clean.description or "")
    assert "Python" in (clean.description or "")


def test_sanitize_rejects_invalid_payloads():
    with pytest.raises(InvalidJobPayload):
        sanitize_job(make_normalized(title="   "))
    with pytest.raises(InvalidJobPayload):
        sanitize_job(make_normalized(job_url="javascript:alert(1)"))
    with pytest.raises(InvalidJobPayload):
        sanitize_job(make_normalized(job_url="not a url"))
    with pytest.raises(InvalidJobPayload):
        sanitize_job(make_normalized(published_at=utcnow() + timedelta(days=3)))


def test_url_normalization_and_fingerprint():
    normalized = validate_job_url(
        "HTTPS://Jobs.Example.com:443/acme/role/?utm_source=linkedin&b=2&a=1#frag"
    )
    assert normalized == "https://jobs.example.com/acme/role?a=1&b=2"
    with pytest.raises(InvalidJobUrlError):
        validate_job_url("ftp://jobs.example.com/role")
    with pytest.raises(InvalidJobUrlError):
        validate_job_url("https://user:pass@jobs.example.com/role")

    one = job_fingerprint(
        job_url=normalized, title="Data Engineer", company_name="Orbit Freight"
    )
    two = job_fingerprint(
        job_url=normalized, title="data   engineer", company_name="ORBIT freight"
    )
    three = job_fingerprint(
        job_url=normalized, title="Data Scientist", company_name="Orbit Freight"
    )
    assert one == two
    assert one != three


def test_ingest_many_counts_and_batch_duplicates(db):
    items = [
        make_normalized(source_job_id="b-1"),
        make_normalized(source_job_id="b-1"),  # duplicate inside the batch
        make_normalized(source_job_id="b-2", job_url="https://jobs.example.com/b2"),
        make_normalized(source_job_id="b-3", job_url="https://jobs.example.com/b3"),
    ]
    stats = ingest_many(db, source="fixtures", items=items, is_test_data=True)
    db.commit()
    assert stats.new_jobs == 3
    assert stats.skipped_jobs == 1
    assert stats.errors

    second = ingest_many(
        db, source="fixtures", items=[items[0], items[2], items[3]], is_test_data=True
    )
    db.commit()
    assert second.new_jobs == 0
    assert second.unchanged_jobs == 3


def test_database_enforces_unique_source_job_id(db):
    make_job(db, source="indeed", source_job_id="dup-1")
    duplicate = Job(
        source="indeed",
        source_job_id="dup-1",
        title="Another role",
        company_name="Other Co",
        job_url="https://jobs.example.com/other",
        work_arrangement="unknown",
        experience_level="unknown",
    )
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(duplicate)
        db.flush()
