"""Small factory helpers for readable tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.constants import (
    ApplicationStatus,
    ExperienceLevel,
    Priority,
    WorkArrangement,
)
from app.core.time import utcnow
from app.models.application import Application
from app.models.fetch_run import JobFetchRun
from app.models.job import Job
from app.models.shortlist import ShortlistedJob
from app.sources.base import NormalizedJob


def make_job(
    db: Session,
    *,
    commit: bool = True,
    **overrides: Any,
) -> Job:
    now = utcnow()
    defaults: dict[str, Any] = {
        "source": "manual_import",
        "source_job_id": f"job-{uuid4().hex}",
        "title": "Backend Engineer",
        "company_name": "Acme Analytics",
        "location": "Karachi, Pakistan",
        "work_arrangement": WorkArrangement.HYBRID,
        "experience_level": ExperienceLevel.MID_SENIOR,
        "description": "Build Python services with FastAPI and PostgreSQL.",
        "job_url": f"https://jobs.example.com/acme/backend-engineer-{uuid4().hex}",
        "published_at": now - timedelta(hours=2),
        "first_seen_at": now - timedelta(hours=1),
        "last_seen_at": now,
        "is_test_data": False,
    }
    defaults.update(overrides)
    job = Job(**defaults)
    db.add(job)
    if commit:
        db.commit()
        db.refresh(job)
    else:
        db.flush()
    return job


def make_shortlist(
    db: Session,
    job: Job,
    *,
    priority: Priority = Priority.MEDIUM,
    notes: str | None = None,
    commit: bool = True,
) -> ShortlistedJob:
    entry = ShortlistedJob(job_id=job.id, priority=priority, notes=notes)
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def make_application(
    db: Session,
    job: Job,
    *,
    status: ApplicationStatus = ApplicationStatus.APPLIED,
    application_date: date | None = None,
    follow_up_date: date | None = None,
    notes: str | None = None,
    resume_reference: str | None = None,
    commit: bool = True,
) -> Application:
    resolved_status = ApplicationStatus(status)
    resolved_date = application_date
    if resolved_date is None and resolved_status is not ApplicationStatus.SAVED:
        resolved_date = utcnow().date()
    application = Application(
        job_id=job.id,
        status=resolved_status,
        application_date=resolved_date,
        follow_up_date=follow_up_date,
        notes=notes,
        resume_reference=resume_reference,
    )
    db.add(application)
    if commit:
        db.commit()
        db.refresh(application)
    else:
        db.flush()
    return application


def make_fetch_run(
    db: Session,
    *,
    source: str = "fixtures",
    status: str = "success",
    started_at: datetime | None = None,
    **overrides: Any,
) -> JobFetchRun:
    from app.core.constants import FetchRunStatus

    run = JobFetchRun(
        source=source,
        status=FetchRunStatus(status),
        started_at=started_at or utcnow(),
        finished_at=started_at or utcnow(),
        **overrides,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def make_normalized(**overrides: Any) -> NormalizedJob:
    defaults = {
        "title": "Data Engineer",
        "company_name": "Orbit Freight",
        "job_url": "https://jobs.example.com/orbit/data-engineer",
        "source_job_id": "ext-1",
        "location": "Remote (Pakistan)",
        "work_arrangement": WorkArrangement.REMOTE,
        "experience_level": ExperienceLevel.MID_SENIOR,
        "description": "Pipelines with Python, Airflow and dbt.",
        "published_at": utcnow() - timedelta(hours=5),
    }
    defaults.update(overrides)
    return NormalizedJob(**defaults)
