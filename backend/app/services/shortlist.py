"""Shortlist operations.

Shortlisting is intentionally independent from applying: creating, updating or
deleting a shortlist entry never touches application records. Refresh/ingest
only updates job columns, so notes and priority survive re-imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.constants import Priority
from app.core.errors import NotFoundError
from app.core.time import utcnow
from app.models.job import Job
from app.models.shortlist import ShortlistedJob
from app.services.jobs import get_job


@dataclass(slots=True)
class ShortlistFilters:
    sources: list[str] | None = None
    priority: Priority | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None
    sort: str = "newest"  # newest | oldest | priority


def _to_datetime_boundary(value: date, *, end: bool) -> datetime:
    boundary = datetime.combine(value, time.min, tzinfo=utcnow().tzinfo)
    return boundary + timedelta(days=1) if end else boundary


def list_shortlist(
    db: Session,
    filters: ShortlistFilters,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ShortlistedJob], int]:
    conditions: list[object] = []
    statement = select(ShortlistedJob).join(ShortlistedJob.job)
    count_statement = select(func.count()).select_from(ShortlistedJob).join(
        ShortlistedJob.job
    )

    if filters.sources:
        conditions.append(Job.source.in_(filters.sources))
    if filters.priority is not None:
        conditions.append(ShortlistedJob.priority == filters.priority)
    if filters.date_from is not None:
        conditions.append(
            ShortlistedJob.created_at >= _to_datetime_boundary(filters.date_from, end=False)
        )
    if filters.date_to is not None:
        conditions.append(
            ShortlistedJob.created_at < _to_datetime_boundary(filters.date_to, end=True)
        )
    if filters.search and filters.search.strip():
        term = filters.search.strip()
        conditions.append(
            Job.title.icontains(term, autoescape=True)
            | Job.company_name.icontains(term, autoescape=True)
            | ShortlistedJob.notes.icontains(term, autoescape=True)
        )

    if conditions:
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)

    total = db.execute(count_statement).scalar_one()

    if filters.sort == "priority":
        statement = statement.order_by(
            case(
                (ShortlistedJob.priority == Priority.HIGH, 0),
                (ShortlistedJob.priority == Priority.MEDIUM, 1),
                else_=2,
            ),
            ShortlistedJob.created_at.desc(),
        )
    elif filters.sort == "oldest":
        statement = statement.order_by(ShortlistedJob.created_at.asc())
    else:
        statement = statement.order_by(ShortlistedJob.created_at.desc())

    statement = statement.offset((page - 1) * page_size).limit(page_size)
    entries = list(db.execute(statement).unique().scalars().all())
    return entries, total


def get_entry(db: Session, job_id: uuid.UUID) -> ShortlistedJob:
    entry = db.execute(
        select(ShortlistedJob).where(ShortlistedJob.job_id == job_id)
    ).scalar_one_or_none()
    if entry is None:
        raise NotFoundError("This job is not on the shortlist")
    return entry


def add_to_shortlist(
    db: Session,
    job_id: uuid.UUID,
    *,
    priority: Priority = Priority.MEDIUM,
    notes: str | None = None,
) -> tuple[ShortlistedJob, bool]:
    """Shortlist a job. Returns ``(entry, created)``; repeated calls update it."""
    job = get_job(db, job_id)
    entry = db.execute(
        select(ShortlistedJob).where(ShortlistedJob.job_id == job.id)
    ).scalar_one_or_none()
    if entry is not None:
        entry.priority = priority
        entry.notes = notes
        db.commit()
        db.expire_all()
        return get_entry(db, job.id), False

    entry = ShortlistedJob(job_id=job.id, priority=priority, notes=notes)
    db.add(entry)
    db.commit()
    db.expire_all()
    return get_entry(db, job.id), True


def update_shortlist(
    db: Session, job_id: uuid.UUID, changes: dict[str, object]
) -> ShortlistedJob:
    entry = get_entry(db, job_id)
    allowed = {"priority", "notes"}
    unknown = set(changes) - allowed
    if unknown:  # pragma: no cover - guarded by schema
        raise ValueError(f"Unsupported shortlist fields: {sorted(unknown)}")
    for field, value in changes.items():
        setattr(entry, field, value)
    entry.updated_at = utcnow()
    db.commit()
    db.expire_all()
    return get_entry(db, job_id)


def remove_from_shortlist(db: Session, job_id: uuid.UUID) -> None:
    entry = get_entry(db, job_id)
    db.delete(entry)
    db.commit()
    db.expire_all()


def shortlist_counts(db: Session, *, include_test_data: bool = True) -> dict[Priority, int]:
    statement = (
        select(ShortlistedJob.priority, func.count())
        .select_from(ShortlistedJob)
        .join(ShortlistedJob.job)
        .group_by(ShortlistedJob.priority)
    )
    if not include_test_data:
        statement = statement.where(Job.is_test_data.is_(False))
    rows = db.execute(statement).all()
    counts = dict.fromkeys(Priority, 0)
    for priority, count in rows:
        counts[priority] = count
    return counts
