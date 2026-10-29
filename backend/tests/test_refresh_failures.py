"""Provider outages and partial batches must be recorded, not crash the API."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app.core.constants import FetchRunStatus, RefreshTrigger, SourceAvailability
from app.core.time import utcnow
from app.models.fetch_run import JobFetchRun
from app.models.job import Job
from app.services.refresh import run_refresh
from app.sources.base import (
    FetchResult,
    JobQuery,
    NormalizedJob,
    SourceAdapter,
    SourceRequestError,
)
from app.sources.registry import SourceRegistry
from tests.factories import make_normalized


class ExplodingAdapter(SourceAdapter):
    key = "exploding"
    name = "Exploding feed"
    description = "Always fails"
    availability = SourceAvailability.AVAILABLE
    supports_refresh = True

    def fetch(self, query: JobQuery) -> FetchResult:
        raise SourceRequestError("Provider returned HTTP 503")


class PartlyBrokenAdapter(SourceAdapter):
    key = "partial"
    name = "Partially broken feed"
    description = "Returns one good and one invalid listing"
    availability = SourceAvailability.AVAILABLE
    supports_refresh = True

    def fetch(self, query: JobQuery) -> FetchResult:
        good = make_normalized(source_job_id="partial-good", title="Platform Engineer")
        bad = NormalizedJob(
            title="Broken",
            company_name="Broken Co",
            job_url="not-a-url",
            source_job_id="partial-bad",
        )
        return FetchResult(jobs=[good, bad], warnings=["Skipped a malformed row"])


class EmptyAdapter(SourceAdapter):
    key = "empty"
    name = "Empty feed"
    description = "No results"
    availability = SourceAvailability.AVAILABLE
    supports_refresh = True

    def fetch(self, query: JobQuery) -> FetchResult:
        return FetchResult(jobs=[])


def test_provider_exception_is_recorded_as_failed_run(db):
    registry = SourceRegistry([ExplodingAdapter()])
    outcome = run_refresh(db, requested_sources=["exploding"], registry=registry)
    assert len(outcome.runs) == 1
    run = outcome.runs[0]
    assert run.status is FetchRunStatus.FAILED
    assert run.finished_at is not None
    assert "503" in (run.error_message or "")
    assert db.execute(select(func.count()).select_from(Job)).scalar_one() == 0


def test_partial_batch_keeps_valid_rows(db):
    registry = SourceRegistry([PartlyBrokenAdapter()])
    outcome = run_refresh(db, requested_sources=["partial"], registry=registry)
    run = outcome.runs[0]
    assert run.status is FetchRunStatus.PARTIAL
    assert run.new_jobs_count == 1
    assert run.fetched_jobs_count == 2
    assert run.error_message and "Invalid job URL" in run.error_message
    assert outcome.warnings["partial"] == ["Skipped a malformed row"]
    assert db.execute(select(func.count()).select_from(Job)).scalar_one() == 1


def test_empty_provider_succeeds_with_zero_counts(db):
    registry = SourceRegistry([EmptyAdapter()])
    outcome = run_refresh(db, requested_sources=["empty"], registry=registry)
    run = outcome.runs[0]
    assert run.status is FetchRunStatus.SUCCESS
    assert run.new_jobs_count == 0
    assert run.error_message is None


def test_unavailable_provider_is_skipped_not_failed(db):
    from app.core.config import get_settings
    from app.sources.registry import build_registry

    registry = build_registry(get_settings())
    outcome = run_refresh(db, requested_sources=["linkedin"], registry=registry)
    run = outcome.runs[0]
    assert run.status is FetchRunStatus.SKIPPED
    assert "scrap" in (run.error_message or "").lower() or "API" in (
        run.error_message or ""
    )


def test_refresh_requires_at_least_one_target(db):
    import pytest

    from app.core.errors import BadRequestError

    with pytest.raises(BadRequestError):
        run_refresh(db, requested_sources=[], registry=SourceRegistry([]))


def test_scheduled_trigger_is_persisted(db):
    registry = SourceRegistry([EmptyAdapter()])
    run_refresh(
        db,
        trigger=RefreshTrigger.SCHEDULED,
        registry=registry,
    )
    run = db.execute(select(JobFetchRun)).scalar_one()
    assert run.trigger is RefreshTrigger.SCHEDULED


def test_scheduler_respects_settings(db, monkeypatch):
    from contextlib import contextmanager

    from app.services import scheduler as scheduler_module
    from app.services.search_settings import get_or_create_settings

    row = get_or_create_settings(db)
    row.scheduled_refresh_enabled = False
    db.commit()

    @contextmanager
    def fake_session():
        yield db

    monkeypatch.setattr(scheduler_module, "SessionLocal", fake_session)
    scheduler = scheduler_module.RefreshScheduler(
        SourceRegistry([EmptyAdapter()]), settings=scheduler_module.get_settings()
    )
    scheduler.run_once()
    assert db.execute(select(func.count()).select_from(JobFetchRun)).scalar_one() == 0

    row.scheduled_refresh_enabled = True
    row.scheduled_refresh_interval_minutes = 15
    db.commit()
    # The first automatic run waits for one full interval after startup.
    scheduler._started_at = utcnow() - timedelta(hours=2)
    scheduler.run_once()
    run = db.execute(select(JobFetchRun)).scalar_one()
    assert run.trigger is RefreshTrigger.SCHEDULED
    assert run.started_at is not None


def test_latest_scheduled_run_helper(db):
    from app.services.refresh import latest_scheduled_run_at

    manual = JobFetchRun(
        source="fixtures",
        status=FetchRunStatus.SUCCESS,
        trigger=RefreshTrigger.MANUAL,
        started_at=utcnow(),
        finished_at=utcnow(),
    )
    scheduled = JobFetchRun(
        source="fixtures",
        status=FetchRunStatus.SUCCESS,
        trigger=RefreshTrigger.SCHEDULED,
        started_at=utcnow() - timedelta(hours=1),
        finished_at=utcnow() - timedelta(hours=1),
    )
    db.add_all([manual, scheduled])
    db.commit()
    latest = latest_scheduled_run_at(db)
    assert latest is not None
    assert latest < manual.started_at
