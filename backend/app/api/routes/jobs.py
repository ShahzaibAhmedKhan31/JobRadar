"""Job discovery, refresh and manual import endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.api.deps import AppSettings, DbSession, PaginationDep, RegistryDep
from app.core.constants import (
    ApplicationStatus,
    ExperienceLevel,
    FetchRunStatus,
    SortOption,
    WorkArrangement,
)
from app.models.fetch_run import JobFetchRun
from app.schemas.common import Page
from app.schemas.job import (
    FacetValue,
    JobDetail,
    JobFacets,
    JobPage,
    ManualImportResponse,
    ManualJobImport,
    PruneJobsRequest,
    PruneJobsResponse,
    job_to_read,
)
from app.schemas.refresh import (
    AppliedQuery,
    FetchRunRead,
    RefreshRequest,
    RefreshResponse,
    RefreshSourceResult,
    fetch_run_to_read,
)
from app.services import jobs as job_service
from app.services.manual_import import import_job
from app.services.refresh import run_refresh
from app.sources.base import JobQuery

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobPage, summary="List stored jobs with filters")
def list_jobs(
    db: DbSession,
    registry: RegistryDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=200, description="Free-text search")] = None,
    titles: Annotated[
        list[str] | None, Query(description="One or more job titles/keywords")
    ] = None,
    keywords: Annotated[
        list[str] | None, Query(description="Additional skills/keywords")
    ] = None,
    location: Annotated[str | None, Query(max_length=200)] = None,
    locations: Annotated[
        list[str] | None,
        Query(description="One or more locations; repeat the parameter, or use newlines"),
    ] = None,
    work_arrangement: Annotated[WorkArrangement | None, Query()] = None,
    experience_level: Annotated[ExperienceLevel | None, Query()] = None,
    sources: Annotated[list[str] | None, Query(description="Source keys")] = None,
    max_age_hours: Annotated[
        int | None, Query(ge=1, le=720, description="Posting age window in hours")
    ] = None,
    include_unknown_published: Annotated[
        bool, Query(description="Include jobs whose publication time is unknown")
    ] = False,
    shortlisted: Annotated[bool | None, Query()] = None,
    application_status: Annotated[list[ApplicationStatus] | None, Query()] = None,
    include_test_data: Annotated[
        bool, Query(description="Include synthetic sample rows (opt-in)")
    ] = False,
    sort: Annotated[SortOption, Query()] = SortOption.NEWEST,
) -> JobPage:
    if sources:
        unknown = set(sources) - registry.known_keys()
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown source key(s): {', '.join(sorted(unknown))}",
            )
    filters = job_service.JobFilters(
        q=q,
        titles=titles or [],
        keywords=keywords or [],
        location=location,
        locations=locations or [],
        work_arrangement=work_arrangement,
        experience_level=experience_level,
        sources=sources or [],
        max_age_hours=max_age_hours,
        include_unknown_published=include_unknown_published,
        shortlisted=shortlisted,
        application_statuses=application_status or [],
        include_test_data=include_test_data,
        sort=sort,
    )
    result = job_service.list_jobs(
        db, filters, page=pagination.page, page_size=pagination.page_size
    )
    items = [
        job_to_read(job, possible_duplicate_count=result.duplicate_counts.get(job.id, 0))
        for job in result.jobs
    ]
    return JobPage.build(
        items,
        total=result.total,
        page=pagination.page,
        page_size=pagination.page_size,
        unknown_published_count=result.unknown_published_count,
        include_test_data=include_test_data,
    )


@router.get(
    "/facets",
    response_model=JobFacets,
    summary="What is stored, independent of the current filters",
)
def get_job_facets(
    db: DbSession,
    sources: Annotated[list[str] | None, Query(description="Source keys")] = None,
    include_test_data: Annotated[bool, Query()] = False,
) -> JobFacets:
    raw = job_service.job_facets(
        db,
        sources=sources or [],
        include_test_data=include_test_data,
    )

    def _values(key: str) -> list[FacetValue]:
        return [FacetValue(value=value, count=count) for value, count in raw[key]]  # type: ignore[misc]

    return JobFacets(
        total=int(raw["total"]),  # type: ignore[arg-type]
        include_test_data=include_test_data,
        real_total=int(raw["real_total"]),  # type: ignore[arg-type]
        sample_total=int(raw["sample_total"]),  # type: ignore[arg-type]
        sources=_values("sources"),
        locations=_values("locations"),
        companies=_values("companies"),
        newest_first_seen_at=raw["newest_first_seen_at"],  # type: ignore[arg-type]
    )


@router.post(
    "/prune",
    response_model=PruneJobsResponse,
    summary="Delete stored listings you never shortlisted or applied to",
)
def prune_stored_jobs(
    payload: PruneJobsRequest, db: DbSession, registry: RegistryDep
) -> PruneJobsResponse:
    """Clean up listings a provider delivered but the user does not want.

    Tracked listings (shortlisted or with an application) are never deleted:
    they represent the user's own work and the foreign keys cascade.
    """
    if payload.sources:
        unknown = set(payload.sources) - registry.known_keys()
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown source key(s): {', '.join(sorted(unknown))}",
            )
    result = job_service.prune_jobs(
        db, sources=payload.sources, include_test_data=payload.include_test_data
    )
    if result.deleted:
        message = f"Removed {result.deleted} stored listing(s)."
    elif result.matched:
        message = "Nothing removed: every matching listing is shortlisted or has an application."
    else:
        message = "Nothing stored matches that scope, so nothing was removed."
    if result.deleted and result.protected:
        message += (
            f" Kept {result.protected} listing(s) you had shortlisted or applied to."
        )
    return PruneJobsResponse(
        deleted=result.deleted,
        protected=result.protected,
        matched=result.matched,
        message=message,
    )


@router.post(
    "/import",
    response_model=ManualImportResponse,
    summary="Record a listing found manually",
    status_code=status.HTTP_201_CREATED,
)
def create_manual_import(
    payload: ManualJobImport,
    db: DbSession,
    response: Response,
) -> ManualImportResponse:
    job, created = import_job(db, payload)
    if not created:
        response.status_code = status.HTTP_200_OK
    duplicates = job_service.find_possible_duplicates(db, job)
    detail = job_to_read(
        job,
        include_description=True,
        possible_duplicate_count=len(duplicates),
        possible_duplicates=duplicates,
    )
    assert isinstance(detail, JobDetail)
    return ManualImportResponse(
        job=detail,
        created=created,
        message=(
            "Job added to JobRadar."
            if created
            else "This listing is already stored; showing the existing record."
        ),
    )


@router.post("/refresh", response_model=RefreshResponse, summary="Refresh job sources")
def refresh_jobs(
    db: DbSession,
    registry: RegistryDep,
    settings: AppSettings,
    payload: RefreshRequest | None = None,
) -> RefreshResponse:
    payload = payload or RefreshRequest()
    limit = min(
        payload.limit or settings.max_refresh_jobs_per_source,
        settings.max_refresh_jobs_per_source,
    )
    query = JobQuery(
        titles=tuple(payload.titles),
        keywords=tuple(payload.keywords),
        location=payload.location,
        locations=tuple(payload.locations),
        max_age_hours=payload.max_age_hours,
        limit=limit,
    )
    outcome = run_refresh(
        db,
        requested_sources=payload.sources,
        query=query,
        registry=registry,
        settings=settings,
    )
    runs = [
        RefreshSourceResult(
            **fetch_run_to_read(run).model_dump(),
            warnings=outcome.warnings.get(run.source, []),
        )
        for run in outcome.runs
    ]
    skipped = sum(1 for run in outcome.runs if run.status is FetchRunStatus.SKIPPED)
    failed = sum(1 for run in outcome.runs if run.status is FetchRunStatus.FAILED)
    applied = None
    if outcome.applied_query is not None:
        requested = list(outcome.applied_query.titles) + list(outcome.applied_query.keywords)
        searched_locations = outcome.applied_locations or list(
            outcome.applied_query.resolved_locations()
        )
        applied = AppliedQuery(
            # Providers may cap how many terms/locations they search; report
            # what actually ran.
            terms=outcome.applied_terms or requested,
            location=searched_locations[0] if searched_locations else None,
            locations=searched_locations,
            max_age_hours=outcome.applied_query.max_age_hours,
            limit=outcome.applied_query.limit,
            sources=[run.source for run in outcome.runs],
        )
    parts: list[str] = []
    if outcome.new_jobs:
        parts.append(f"{outcome.new_jobs} new")
    if outcome.updated_jobs:
        parts.append(f"{outcome.updated_jobs} updated")
    if not parts:
        parts.append("no changes")
    message = "Refresh finished: " + ", ".join(parts) + " job(s)."
    if skipped:
        message += f" {skipped} source(s) skipped."
    if failed:
        message += f" {failed} source(s) failed."
    if applied is not None and not outcome.new_jobs:
        # Nothing came back: say exactly what was asked so the user can compare
        # it with a search that works for them.
        message += f" Searched {applied.summary()}."
    if applied is not None and outcome.location_source == "default" and applied.locations:
        default_places = ", ".join(applied.locations[:3])
        message += (
            f" No location was set, so the default ({default_places}) was used —"
            " change it in Search Settings."
        )
    return RefreshResponse(
        runs=runs,
        new_jobs=outcome.new_jobs,
        updated_jobs=outcome.updated_jobs,
        message=message,
        applied_query=applied,
    )


@router.get(
    "/refresh-history",
    response_model=Page[FetchRunRead],
    summary="Recent source refresh runs",
)
def refresh_history(
    db: DbSession,
    pagination: PaginationDep,
    source: Annotated[str | None, Query(max_length=50)] = None,
    run_status: Annotated[FetchRunStatus | None, Query(alias="status")] = None,
) -> Page[FetchRunRead]:
    conditions = []
    if source:
        conditions.append(JobFetchRun.source == source)
    if run_status is not None:
        conditions.append(JobFetchRun.status == run_status)
    total = db.execute(
        select(func.count()).select_from(JobFetchRun).where(*conditions)
    ).scalar_one()
    runs = (
        db.execute(
            select(JobFetchRun)
            .where(*conditions)
            .order_by(JobFetchRun.started_at.desc())
            .offset((pagination.page - 1) * pagination.page_size)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )
    items = [fetch_run_to_read(run) for run in runs]
    return Page.build(
        items, total=total, page=pagination.page, page_size=pagination.page_size
    )


@router.get("/{job_id}", response_model=JobDetail, summary="Retrieve a job")
def get_job_detail(job_id: uuid.UUID, db: DbSession) -> JobDetail:
    job = job_service.get_job(db, job_id)
    duplicates = job_service.find_possible_duplicates(db, job)
    detail = job_to_read(
        job,
        include_description=True,
        possible_duplicate_count=len(duplicates),
        possible_duplicates=duplicates,
    )
    assert isinstance(detail, JobDetail)
    return detail
