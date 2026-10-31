"""Manual and scheduled source refresh orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.constants import FetchRunStatus, RefreshTrigger
from app.core.errors import BadRequestError
from app.core.logging import get_logger
from app.core.text import split_locations, split_terms
from app.core.time import ensure_utc, utcnow
from app.models.fetch_run import JobFetchRun
from app.services.ingestion import ingest_many
from app.services.search_settings import get_settings_row
from app.sources.base import JobQuery, SourceAdapter
from app.sources.registry import SourceRegistry

logger = get_logger(__name__)

MAX_ERROR_MESSAGE_LENGTH = 4000


#: Human labels for the country keys jobspy expects (``country_indeed``).
COUNTRY_LABELS: dict[str, str] = {
    "usa": "United States",
    "us": "United States",
    "united states": "United States",
    "uk": "United Kingdom",
    "gb": "United Kingdom",
    "uae": "United Arab Emirates",
    "ae": "United Arab Emirates",
}

#: Where the location sent to the providers came from.
LOCATION_REQUEST = "request"
LOCATION_SAVED = "saved"
LOCATION_DEFAULT = "default"
LOCATION_NONE = "none"


@dataclass(slots=True)
class RefreshOutcome:
    runs: list[JobFetchRun] = field(default_factory=list)
    warnings: dict[str, list[str]] = field(default_factory=dict)
    #: Search hints that were resolved (request → saved Search Settings → defaults).
    applied_query: JobQuery | None = None
    #: Terms the providers were actually queried with, after provider-side caps.
    applied_terms: list[str] = field(default_factory=list)
    #: Locations the providers were actually queried with, after caps.
    applied_locations: list[str] = field(default_factory=list)
    #: ``request`` / ``saved`` / ``default`` / ``none`` — see ``LOCATION_*``.
    location_source: str = LOCATION_NONE

    @property
    def new_jobs(self) -> int:
        return sum(run.new_jobs_count for run in self.runs)

    @property
    def updated_jobs(self) -> int:
        return sum(run.updated_jobs_count for run in self.runs)


def default_search_location(settings: Settings) -> str | None:
    """Location to fall back to when nobody supplied one.

    ``JOBSPY_DEFAULT_LOCATION`` wins; otherwise the configured country is used
    as a human-readable place (``pakistan`` -> ``Pakistan``). Returning ``None``
    means "nowhere to search", which the caller must treat as "do not scrape":
    a board queried without a location answers with a US-wide feed.
    """
    explicit = (settings.jobspy_default_location or "").strip()
    if explicit:
        return explicit
    country = (settings.jobspy_country or "").strip()
    if not country:
        return None
    return COUNTRY_LABELS.get(country.lower(), country.replace("_", " ").title())


def resolve_search_scope(
    db: Session, query: JobQuery | None, *, settings: Settings | None = None
) -> tuple[JobQuery, str]:
    """Fill empty search hints and report where the location came from.

    Order of precedence: the request's own hints, then the persisted Search
    Settings row, then the configured default location. Any hint supplied in the
    request wins, so the Discover page can override the saved search.
    """
    settings = settings or get_settings()
    base = query or JobQuery(limit=settings.max_refresh_jobs_per_source)
    titles = base.titles
    keywords = base.keywords
    locations = list(base.resolved_locations())
    max_age_hours = base.max_age_hours
    location_source = LOCATION_REQUEST if locations else LOCATION_NONE

    row = get_settings_row(db)
    if row is not None:
        titles = titles or tuple(split_terms([row.default_titles]))
        keywords = keywords or tuple(split_terms([row.default_keywords]))
        max_age_hours = max_age_hours or row.default_posting_age_hours
        if not locations and row.default_location:
            locations = split_locations([row.default_location])
            location_source = LOCATION_SAVED if locations else LOCATION_NONE

    if not locations:
        fallback = default_search_location(settings)
        if fallback:
            locations = split_locations([fallback])
            location_source = LOCATION_DEFAULT if locations else LOCATION_NONE

    return (
        replace(
            base,
            titles=titles,
            keywords=keywords,
            location=locations[0] if locations else None,
            locations=tuple(locations),
            max_age_hours=max_age_hours,
        ),
        location_source,
    )


def apply_saved_search(
    db: Session, query: JobQuery | None, *, settings: Settings | None = None
) -> JobQuery:
    """Fill empty search hints from the persisted Search Settings row."""
    return resolve_search_scope(db, query, settings=settings)[0]


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

    fetch_query, location_source = resolve_search_scope(db, query, settings=settings)
    needs_scope = any(
        adapter.requires_search_scope and adapter.can_refresh for adapter in targets
    )
    if needs_scope and not (
        fetch_query.titles or fetch_query.keywords or fetch_query.resolved_locations()
    ):
        raise BadRequestError(
            "A refresh needs at least a job title or a location. Without either, "
            "LinkedIn answers with an unfiltered US-wide feed. Set a default "
            "location in Search Settings (or type one on the Discover page) and "
            "try again."
        )
    outcome = RefreshOutcome(applied_query=fetch_query, location_source=location_source)

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
            for term in result.applied_terms:
                if term not in outcome.applied_terms:
                    outcome.applied_terms.append(term)
            for place in result.applied_locations:
                if place not in outcome.applied_locations:
                    outcome.applied_locations.append(place)
            errors = [*result.errors, *stats.errors]
            if result.errors and not result.jobs:
                # The provider itself failed and produced nothing: this is a
                # failed run, not an empty one.
                _finish_run(
                    db,
                    run,
                    status=FetchRunStatus.FAILED,
                    error_message="; ".join(errors),
                )
                outcome.runs.append(run)
                continue
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
