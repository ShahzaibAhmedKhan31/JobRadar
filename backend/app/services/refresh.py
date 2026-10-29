"""Manual and scheduled source refresh orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.constants import FetchRunStatus, RefreshTrigger
from app.core.errors import BadRequestError
from app.core.logging import get_logger
from app.core.time import ensure_utc, utcnow
from app.models.fetch_run import JobFetchRun
from app.services.ingestion import ingest_many
from app.sources.base import JobQuery, SourceAdapter
from app.sources.registry import SourceRegistry

logger = get_logger(__name__)

MAX_ERROR_MESSAGE_LENGTH = 4000


@dataclass(slots=True)
class RefreshOutcome:
    runs: list[JobFetchRun] = field(default_factory=list)
    warnings: dict[str, list[str]] = field(default_factory=dict)

    @property
    def new_jobs(self) -> int:
        return sum(run.new_jobs_count for run in self.runs)

    @property
    def updated_jobs(self) -> int:
        return sum(run.updated_jobs_count for run in self.runs)


def _finish_run(
    db: Session,
    run: JobFetchRun,
    *,
    status: FetchRunStatus,
    error_message: str | None = None,
    fetched: int = 0,
    new: int = 0,
    updated: int = 0,
    unchanged: int = 0,
) -> None:
    run.status = status
    run.finished_at = utcnow()
    run.fetched_jobs_count = fetched
    run.new_jobs_count = new
    run.updated_jobs_count = updated
    run.unchanged_jobs_count = unchanged
    run.error_message = error_message[:MAX_ERROR_MESSAGE_LENGTH] if error_message else None
    db.commit()


def run_refresh(
    db: Session,
    *,
    requested_sources: list[str] | None = None,
    trigger: RefreshTrigger = RefreshTrigger.MANUAL,
    query: JobQuery | None = None,
    registry: SourceRegistry,
    settings: Settings | None = None,
) -> RefreshOutcome:
    """Attempt a refresh for the requested (or all refreshable) sources."""
    settings = settings or get_settings()
    targets: list[SourceAdapter] = registry.refresh_targets(
        requested_sources, settings.enabled_sources
    )
    if not targets:
        raise BadRequestError(
            "No refreshable job sources are configured. Enable a source provider or "
            "record listings through manual import."
        )

    fetch_query = query or JobQuery(limit=settings.max_refresh_jobs_per_source)
    outcome = RefreshOutcome()

    for adapter in targets:
        run = JobFetchRun(
            source=adapter.key,
            trigger=trigger,
            status=FetchRunStatus.RUNNING,
            started_at=utcnow(),
        )
        db.add(run)
        db.commit()

        if not adapter.can_refresh:
            reason = adapter.availability_reason or "Source is not available."
            _finish_run(db, run, status=FetchRunStatus.SKIPPED, error_message=reason)
            outcome.runs.append(run)
            continue

        try:
            result = adapter.fetch(fetch_query)
            stats = ingest_many(
                db,
                source=adapter.key,
                items=result.jobs,
                is_test_data=adapter.is_test_data,
            )
            if result.warnings:
                outcome.warnings[adapter.key] = result.warnings
            errors = stats.errors
            status = FetchRunStatus.SUCCESS if not errors else FetchRunStatus.PARTIAL
            _finish_run(
                db,
                run,
                status=status,
                error_message="; ".join(errors) if errors else None,
                fetched=stats.fetched_jobs,
                new=stats.new_jobs,
                updated=stats.updated_jobs,
                unchanged=stats.unchanged_jobs,
            )
            logger.info(
                "Refresh %s finished: %s new, %s updated, %s unchanged, %s skipped",
                adapter.key,
                stats.new_jobs,
                stats.updated_jobs,
                stats.unchanged_jobs,
                stats.skipped_jobs,
            )
        except Exception as exc:
            logger.exception("Refresh failed for source %s", adapter.key)
            db.rollback()
            run = db.get(JobFetchRun, run.id) or run
            message = str(exc) or exc.__class__.__name__
            _finish_run(
                db,
                run,
                status=FetchRunStatus.FAILED,
                error_message=message,
            )
        outcome.runs.append(run)
    return outcome


def latest_scheduled_run_at(
    db: Session, source_keys: list[str] | None = None
) -> datetime | None:
    statement = select(func.max(JobFetchRun.started_at)).where(
        JobFetchRun.trigger == RefreshTrigger.SCHEDULED
    )
    if source_keys:
        statement = statement.where(JobFetchRun.source.in_(source_keys))
    value = db.execute(statement).scalar_one_or_none()
    return ensure_utc(value)
