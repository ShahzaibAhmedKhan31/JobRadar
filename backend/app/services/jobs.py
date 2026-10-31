"""Job listing queries: filtering, sorting, pagination and duplicate hints."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import Select, and_, case, delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    ApplicationStatus,
    ExperienceLevel,
    SortOption,
    WorkArrangement,
)
from app.core.errors import NotFoundError
from app.core.text import normalize_key, split_terms
from app.core.time import ensure_utc, utcnow
from app.models.application import Application
from app.models.job import Job
from app.models.shortlist import ShortlistedJob

REMOTE_TERMS = {"remote", "anywhere", "remote only", "work from home"}


@dataclass(slots=True)
class JobFilters:
    q: str | None = None
    titles: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    location: str | None = None
    work_arrangement: WorkArrangement | None = None
    experience_level: ExperienceLevel | None = None
    sources: list[str] = field(default_factory=list)
    max_age_hours: int | None = None
    include_unknown_published: bool = False
    shortlisted: bool | None = None
    application_statuses: list[ApplicationStatus] = field(default_factory=list)
    include_test_data: bool = True
    sort: SortOption = SortOption.NEWEST

    def search_terms(self) -> list[str]:
        return split_terms([self.q] if self.q else [], max_terms=5)


@dataclass(slots=True)
class JobListResult:
    jobs: list[Job]
    total: int
    unknown_published_count: int
    duplicate_counts: dict[uuid.UUID, int] = field(default_factory=dict)


@dataclass(slots=True)
class PruneResult:
    """Outcome of removing stored listings."""

    #: Rows deleted.
    deleted: int = 0
    #: Rows that matched the scope but were kept because they are tracked.
    protected: int = 0
    #: Rows that matched the scope before the tracked-job protection.
    matched: int = 0


def _any_field_conditions(term: str, fields: tuple[object, ...]) -> object:
    return or_(*(field.icontains(term, autoescape=True) for field in fields))  # type: ignore[attr-defined]


def _base_conditions(filters: JobFilters) -> list[object]:
    conditions: list[object] = []
    if not filters.include_test_data:
        conditions.append(Job.is_test_data.is_(False))

    for term in filters.search_terms():
        conditions.append(
            _any_field_conditions(
                term,
                (Job.title, Job.company_name, Job.location, Job.description),
            )
        )

    title_terms = split_terms(filters.titles)
    if title_terms:
        conditions.append(
            or_(
                *(
                    _any_field_conditions(term, (Job.title, Job.description))
                    for term in title_terms
                )
            )
        )

    keyword_terms = split_terms(filters.keywords)
    if keyword_terms:
        conditions.append(
            or_(
                *(
                    _any_field_conditions(
                        term,
                        (Job.title, Job.company_name, Job.location, Job.description),
                    )
                    for term in keyword_terms
                )
            )
        )

    if filters.location and filters.location.strip():
        conditions.append(location_conditions(filters.location))

    if filters.work_arrangement is not None:
        conditions.append(Job.work_arrangement == filters.work_arrangement)
    if filters.experience_level is not None:
        conditions.append(Job.experience_level == filters.experience_level)
    if filters.sources:
        conditions.append(Job.source.in_(filters.sources))

    if filters.shortlisted is True:
        conditions.append(Job.id.in_(select(ShortlistedJob.job_id)))
    elif filters.shortlisted is False:
        conditions.append(Job.id.not_in(select(ShortlistedJob.job_id)))

    if filters.application_statuses:
        conditions.append(
            Job.id.in_(
                select(Application.job_id).where(
                    Application.status.in_(filters.application_statuses)
                )
            )
        )
    return conditions


def _count(db: Session, statement: object) -> int:
    return int(db.execute(statement).scalar_one())  # type: ignore[arg-type]


def job_facets(
    db: Session,
    *,
    sources: list[str] | None = None,
    include_test_data: bool = False,
    limit: int = 12,
) -> dict[str, object]:
    """Counts of stored jobs by source/location/company for the empty state."""
    scope: list[object] = []
    if sources:
        scope.append(Job.source.in_(sources))

    def _scoped(*extra: object) -> list[object]:
        return [*scope, *extra]

    total = _count(db, select(func.count()).select_from(Job).where(*_scoped()))
    real_total = _count(
        db,
        select(func.count()).select_from(Job).where(*_scoped(Job.is_test_data.is_(False))),
    )
    sample_total = _count(
        db,
        select(func.count()).select_from(Job).where(*_scoped(Job.is_test_data.is_(True))),
    )
    data_scope = [] if include_test_data else [Job.is_test_data.is_(False)]

    def _group(column: object) -> list[tuple[str, int]]:
        rows = db.execute(
            select(column, func.count())  # type: ignore[arg-type]
            .select_from(Job)
            .where(*_scoped(*data_scope), column.is_not(None))  # type: ignore[attr-defined]
            .group_by(column)  # type: ignore[arg-type]
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [(str(value), int(count)) for value, count in rows if value]

    newest = db.execute(
        select(func.max(Job.first_seen_at)).where(*_scoped(*data_scope))
    ).scalar_one_or_none()
    return {
        "total": total,
        "include_test_data": include_test_data,
        "real_total": real_total,
        "sample_total": sample_total,
        "sources": _group(Job.source),
        "locations": _group(Job.location),
        "companies": _group(Job.company_name),
        "newest_first_seen_at": ensure_utc(newest),
    }


def prune_jobs(
    db: Session,
    *,
    sources: list[str] | None = None,
    include_test_data: bool = False,
) -> PruneResult:
    """Delete stored listings that the user never acted on.

    Scrapers can leave perfectly good but irrelevant rows behind (for example a
    US-wide feed fetched before a location was configured). Removing them is the
    only way back to a clean list, but a listing that was shortlisted or turned
    into an application is the user's own work: those rows are always kept,
    whatever the scope, because deleting a job cascades to its shortlist entry
    and application.
    """
    conditions: list[object] = []
    if sources:
        conditions.append(Job.source.in_(sources))
    if not include_test_data:
        conditions.append(Job.is_test_data.is_(False))

    tracked: object = or_(
        Job.id.in_(select(ShortlistedJob.job_id)),
        Job.id.in_(select(Application.job_id)),
    )
    matched = _count(db, select(func.count()).select_from(Job).where(*conditions))
    protected = _count(
        db, select(func.count()).select_from(Job).where(*conditions, tracked)
    )
    result = db.execute(
        delete(Job)
        .where(*conditions, ~tracked)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return PruneResult(
        deleted=int(result.rowcount or 0), protected=protected, matched=matched
    )


def published_since(cutoff: datetime) -> object:
    """Freshness predicate that respects date-only publication timestamps.

    For rows where the provider reported only a calendar date, ``published_at``
    is midnight UTC of that day. The true posting moment is somewhere inside
    ``[published_at, published_at + 24h)``, so the row belongs to the window
    whenever that day overlaps it — expressed without interval arithmetic so it
    works on both PostgreSQL and SQLite.
    """
    return or_(
        Job.published_at >= cutoff,
        and_(
            Job.published_at_is_date_only.is_(True),
            Job.published_at > cutoff - timedelta(days=1),
        ),
    )


def location_conditions(location: str) -> object:
    """Match a typed location against free-text provider locations.

    Providers do not normalize locations, so an exact substring test fails on
    perfectly reasonable input: "Karachi, Pakistan" is not a substring of
    "Karachi, Sindh, Pakistan", and "Karachi" is not a substring of
    "Karachi Division". Every meaningful token therefore has to be present
    (AND), which keeps "Karachi, Pakistan" matching both forms while still
    rejecting "United Arab Emirates".
    """
    cleaned = location.strip()
    tokens = [token for token in split_terms([cleaned], max_terms=6) if len(token) > 1]
    if not tokens:
        tokens = [cleaned]
    conditions: list[object] = [
        Job.location.icontains(token, autoescape=True) for token in tokens
    ]
    combined: object = and_(*conditions) if len(conditions) > 1 else conditions[0]
    if cleaned.lower() in REMOTE_TERMS:
        combined = or_(combined, Job.work_arrangement == WorkArrangement.REMOTE)
    return combined


def _published_window_condition(
    filters: JobFilters, *, now: datetime
) -> object | None:
    if not filters.max_age_hours:
        return None
    cutoff = now - timedelta(hours=filters.max_age_hours)
    window: object = published_since(cutoff)
    if filters.include_unknown_published:
        window = or_(window, Job.published_at.is_(None))
    return window


def _relevance_expression(filters: JobFilters) -> object | None:
    terms = [*split_terms(filters.titles), *split_terms(filters.keywords), *filters.search_terms()]
    unique_terms: list[str] = []
    for term in terms:
        if term.casefold() not in {existing.casefold() for existing in unique_terms}:
            unique_terms.append(term)
    if not unique_terms:
        return None
    score = case(
        (
            or_(*(Job.title.icontains(term, autoescape=True) for term in unique_terms[:10])),
            10,
        ),
        else_=0,
    ) + case(
        (
            or_(
                *(
                    Job.company_name.icontains(term, autoescape=True)
                    for term in unique_terms[:10]
                )
            ),
            4,
        ),
        else_=0,
    ) + case(
        (
            or_(
                *(
                    Job.description.icontains(term, autoescape=True)
                    for term in unique_terms[:10]
                )
            ),
            2,
        ),
        else_=0,
    )
    return score


def _apply_sort(statement: Select, filters: JobFilters) -> Select:
    if filters.sort is SortOption.RELEVANT:
        relevance = _relevance_expression(filters)
        if relevance is not None:
            return statement.order_by(
                relevance.desc(),
                Job.published_at.desc().nulls_last(),
                Job.first_seen_at.desc(),
            )
        return statement.order_by(
            Job.published_at.desc().nulls_last(), Job.first_seen_at.desc()
        )
    if filters.sort is SortOption.OLDEST:
        return statement.order_by(
            Job.published_at.asc().nulls_last(), Job.first_seen_at.asc()
        )
    if filters.sort is SortOption.COMPANY:
        return statement.order_by(
            Job.company_name.asc(), Job.published_at.desc().nulls_last()
        )
    return statement.order_by(
        Job.published_at.desc().nulls_last(), Job.first_seen_at.desc()
    )


def list_jobs(
    db: Session,
    filters: JobFilters,
    *,
    page: int = 1,
    page_size: int = 20,
    now: datetime | None = None,
) -> JobListResult:
    now = ensure_utc(now) or utcnow()
    base = _base_conditions(filters)
    window = _published_window_condition(filters, now=now)

    statement = select(Job).where(*base)
    if window is not None:
        statement = statement.where(window)

    count_statement = select(func.count()).select_from(Job).where(*base)
    if window is not None:
        count_statement = count_statement.where(window)
    total = db.execute(count_statement).scalar_one()

    statement = _apply_sort(statement, filters)
    statement = statement.offset((page - 1) * page_size).limit(page_size)
    jobs = list(db.execute(statement).unique().scalars().all())

    unknown_published = 0
    if filters.max_age_hours:
        unknown_published = db.execute(
            select(func.count())
            .select_from(Job)
            .where(*base, Job.published_at.is_(None))
        ).scalar_one()

    return JobListResult(
        jobs=jobs,
        total=total,
        unknown_published_count=unknown_published,
        duplicate_counts=duplicate_counts(db, jobs),
    )


def get_job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise NotFoundError("Job not found")
    return job


def duplicate_counts(db: Session, jobs: list[Job]) -> dict[uuid.UUID, int]:
    """Count listings that look like the same role (same company + title).

    Sources are deliberately kept separate; the UI only flags them as possible
    duplicates and never merges records automatically.
    """
    if not jobs:
        return {}
    companies = {job.company_name.casefold() for job in jobs}
    candidates = (
        db.execute(select(Job).where(func.lower(Job.company_name).in_(companies)))
        .unique()
        .scalars()
        .all()
    )
    groups: dict[tuple[str, str], list[uuid.UUID]] = {}
    for candidate in candidates:
        key = (normalize_key(candidate.company_name), normalize_key(candidate.title))
        groups.setdefault(key, []).append(candidate.id)

    counts: dict[uuid.UUID, int] = {}
    for job in jobs:
        key = (normalize_key(job.company_name), normalize_key(job.title))
        counts[job.id] = max(0, len(groups.get(key, [])) - 1)
    return counts


def find_possible_duplicates(db: Session, job: Job) -> list[Job]:
    candidates = (
        db.execute(
            select(Job).where(
                func.lower(Job.company_name) == job.company_name.casefold(),
                Job.id != job.id,
            )
        )
        .unique()
        .scalars()
        .all()
    )
    title_key = normalize_key(job.title)
    matches = [
        candidate
        for candidate in candidates
        if normalize_key(candidate.title) == title_key
    ]
    def sort_key(candidate: Job) -> float:
        published = ensure_utc(candidate.published_at)
        return published.timestamp() if published else 0.0

    matches.sort(key=sort_key, reverse=True)
    return matches
