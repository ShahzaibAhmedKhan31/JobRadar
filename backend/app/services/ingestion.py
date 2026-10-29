"""Job normalization, dedupe and upsert.

Dedupe strategy
---------------
1. Preferred key: ``(source, source_job_id)`` enforced by a partial unique index.
2. Fallback (no provider id): ``(source, external_key)`` where ``external_key``
   is a SHA-256 fingerprint of canonical URL + normalized title + company.
3. A ``(job_url)`` match inside the same source is also treated as the same
   listing, which keeps pasted/imported duplicates out of the database.

``published_at`` is only filled in the first time we learn it; later refreshes
never overwrite it, so posting age stays stable and is never synthesized from
``first_seen_at``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.text import clean_text
from app.core.time import ensure_utc, utcnow
from app.core.urls import InvalidJobUrlError, job_fingerprint, validate_job_url
from app.models.job import Job
from app.sources.base import NormalizedJob

logger = get_logger(__name__)

MAX_TITLE_LENGTH = 300
MAX_COMPANY_LENGTH = 200
MAX_LOCATION_LENGTH = 250
MAX_DESCRIPTION_LENGTH = 20_000
MAX_SOURCE_JOB_ID_LENGTH = 255
#: Tolerate small clock differences between providers and our host.
FUTURE_PUBLISH_TOLERANCE = timedelta(hours=24)


class InvalidJobPayload(ValueError):
    """A provider entry cannot be safely stored."""


@dataclass(slots=True)
class UpsertOutcome:
    kind: str  # "new" | "updated" | "unchanged"
    job: Job


@dataclass(slots=True)
class IngestionStats:
    new_jobs: int = 0
    updated_jobs: int = 0
    unchanged_jobs: int = 0
    skipped_jobs: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def fetched_jobs(self) -> int:
        return (
            self.new_jobs + self.updated_jobs + self.unchanged_jobs + self.skipped_jobs
        )

    def record(self, kind: str) -> None:
        if kind == "new":
            self.new_jobs += 1
        elif kind == "updated":
            self.updated_jobs += 1
        else:
            self.unchanged_jobs += 1


def sanitize_job(item: NormalizedJob, *, now: datetime | None = None) -> NormalizedJob:
    """Validate and clean a provider payload before it reaches the database."""
    now = ensure_utc(now) or utcnow()

    title = clean_text(item.title, max_length=MAX_TITLE_LENGTH)
    if not title:
        raise InvalidJobPayload("Job title is missing")

    company = clean_text(item.company_name, max_length=MAX_COMPANY_LENGTH)
    if not company:
        raise InvalidJobPayload("Company name is missing")

    try:
        job_url = validate_job_url(item.job_url)
    except InvalidJobUrlError as exc:
        raise InvalidJobPayload(f"Invalid job URL: {exc}") from exc

    source_job_id = clean_text(item.source_job_id, max_length=MAX_SOURCE_JOB_ID_LENGTH)
    published_at = ensure_utc(item.published_at)
    if published_at is not None and published_at > now + FUTURE_PUBLISH_TOLERANCE:
        raise InvalidJobPayload("Publication timestamp is in the future")

    return NormalizedJob(
        title=title,
        company_name=company,
        job_url=job_url,
        source_job_id=source_job_id,
        location=clean_text(item.location, max_length=MAX_LOCATION_LENGTH),
        work_arrangement=item.work_arrangement,
        experience_level=item.experience_level,
        description=clean_text(item.description, max_length=MAX_DESCRIPTION_LENGTH),
        published_at=published_at,
    )


def find_existing_job(db: Session, source: str, item: NormalizedJob) -> Job | None:
    if item.source_job_id:
        existing = db.execute(
            select(Job).where(
                Job.source == source, Job.source_job_id == item.source_job_id
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    normalized_url = item.job_url.lower()
    by_url = db.execute(
        select(Job).where(Job.source == source, func.lower(Job.job_url) == normalized_url)
    ).scalars().first()
    if by_url is not None:
        return by_url

    if item.source_job_id is None:
        fingerprint = job_fingerprint(
            job_url=item.job_url,
            title=item.title,
            company_name=item.company_name,
        )
        return db.execute(
            select(Job).where(Job.source == source, Job.external_key == fingerprint)
        ).scalar_one_or_none()
    return None


def _apply_update(job: Job, item: NormalizedJob) -> bool:
    """Copy refreshed fields onto an existing row; return True if anything changed."""
    changed = False

    def assign(attr: str, value: object) -> None:
        nonlocal changed
        if getattr(job, attr) != value:
            setattr(job, attr, value)
            changed = True

    assign("title", item.title)
    assign("company_name", item.company_name)
    assign("location", item.location)
    assign("work_arrangement", item.work_arrangement)
    assign("experience_level", item.experience_level)
    assign("description", item.description)
    assign("job_url", item.job_url)
    if not job.source_job_id and item.source_job_id:
        assign("source_job_id", item.source_job_id)
    # Never overwrite a known publication timestamp, and never invent one.
    if job.published_at is None and item.published_at is not None:
        assign("published_at", item.published_at)
    return changed


def upsert_job(
    db: Session,
    *,
    source: str,
    item: NormalizedJob,
    is_test_data: bool = False,
    now: datetime | None = None,
) -> UpsertOutcome:
    """Insert or refresh a single normalized listing."""
    now = ensure_utc(now) or utcnow()
    clean = sanitize_job(item, now=now)
    existing = find_existing_job(db, source, clean)

    if existing is not None:
        changed = _apply_update(existing, clean)
        existing.last_seen_at = now
        db.flush()
        return UpsertOutcome(kind="updated" if changed else "unchanged", job=existing)

    job = Job(
        source=source,
        source_job_id=clean.source_job_id,
        external_key=(
            None
            if clean.source_job_id
            else job_fingerprint(
                job_url=clean.job_url,
                title=clean.title,
                company_name=clean.company_name,
            )
        ),
        title=clean.title,
        company_name=clean.company_name,
        location=clean.location,
        work_arrangement=clean.work_arrangement,
        experience_level=clean.experience_level,
        description=clean.description,
        job_url=clean.job_url,
        published_at=clean.published_at,
        first_seen_at=now,
        last_seen_at=now,
        is_test_data=is_test_data,
    )
    db.add(job)
    db.flush()
    return UpsertOutcome(kind="new", job=job)


def ingest_many(
    db: Session,
    *,
    source: str,
    items: list[NormalizedJob],
    is_test_data: bool = False,
    now: datetime | None = None,
) -> IngestionStats:
    """Upsert a provider batch, isolating failures per row."""
    now = ensure_utc(now) or utcnow()
    stats = IngestionStats()
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()

    for item in items:
        key = item.source_job_id or item.job_url.lower()
        if key in seen_ids or item.job_url.lower() in seen_urls:
            stats.skipped_jobs += 1
            stats.errors.append(
                f"Duplicate entry inside provider batch skipped: {item.title!r}"
            )
            continue
        seen_ids.add(key)
        seen_urls.add(item.job_url.lower())

        try:
            with db.begin_nested():
                outcome = upsert_job(
                    db, source=source, item=item, is_test_data=is_test_data, now=now
                )
        except InvalidJobPayload as exc:
            stats.skipped_jobs += 1
            stats.errors.append(str(exc))
        except IntegrityError as exc:
            stats.skipped_jobs += 1
            logger.warning("Integrity error while ingesting %r: %s", item.title, exc)
            stats.errors.append(
                f"Duplicate or constraint conflict skipped: {item.title!r}"
            )
        else:
            stats.record(outcome.kind)
    return stats
