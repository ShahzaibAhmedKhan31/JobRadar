"""Dashboard aggregations computed from stored records only."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    ACTIVE_APPLICATION_STATUSES,
    APPLICATION_STATUS_LABELS,
    APPLICATION_STATUS_ORDER,
    IN_PROGRESS_APPLICATION_STATUSES,
    ApplicationStatus,
)
from app.core.time import date_range_days, ensure_utc, utcnow
from app.models.application import Application
from app.models.fetch_run import JobFetchRun
from app.models.job import Job
from app.models.shortlist import ShortlistedJob
from app.schemas.dashboard import (
    ActivityPoint,
    ActivityResponse,
    DashboardSummary,
    SourceBreakdownItem,
    StatusBreakdownItem,
)
from app.schemas.job import job_to_read
from app.schemas.refresh import fetch_run_to_read
from app.services.jobs import duplicate_counts, published_since
from app.sources.labels import source_label


def _job_scope(include_test_data: bool) -> list[object]:
    return [] if include_test_data else [Job.is_test_data.is_(False)]


def _count(db: Session, statement) -> int:  # type: ignore[no-untyped-def]
    return int(db.execute(statement).scalar_one())


def get_summary(
    db: Session,
    *,
    recent_period_hours: int = 24,
    include_test_data: bool = False,
    now: datetime | None = None,
) -> DashboardSummary:
    now = ensure_utc(now) or utcnow()
    cutoff = now - timedelta(hours=recent_period_hours)
    scope = _job_scope(include_test_data)

    total_jobs = _count(
        db, select(func.count()).select_from(Job).where(*scope)
    )
    jobs_discovered_recent = _count(
        db,
        select(func.count())
        .select_from(Job)
        .where(*scope, Job.first_seen_at >= cutoff),
    )
    jobs_published_recent = _count(
        db,
        select(func.count())
        .select_from(Job)
        .where(*scope, published_since(cutoff)),
    )
    unknown_published_jobs = _count(
        db,
        select(func.count())
        .select_from(Job)
        .where(*scope, Job.published_at.is_(None)),
    )
    test_data_jobs = _count(
        db,
        select(func.count()).select_from(Job).where(Job.is_test_data.is_(True)),
    )

    shortlisted_jobs = _count(
        db,
        select(func.count())
        .select_from(ShortlistedJob)
        .join(ShortlistedJob.job)
        .where(*scope),
    )

    status_rows = db.execute(
        select(Application.status, func.count())
        .select_from(Application)
        .join(Application.job)
        .where(*scope)
        .group_by(Application.status)
    ).all()
    counts = dict.fromkeys(ApplicationStatus, 0)
    for status, count in status_rows:
        counts[status] = int(count)

    applications_total = sum(counts.values())
    applications_submitted = sum(
        count for status, count in counts.items() if status.is_submitted
    )
    applications_in_progress = sum(
        counts[status] for status in IN_PROGRESS_APPLICATION_STATUSES
    )

    recent_jobs_rows = list(
        db.execute(
            select(Job)
            .where(*scope)
            .order_by(Job.first_seen_at.desc())
            .limit(5)
        )
        .unique()
        .scalars()
        .all()
    )
    dup_counts = duplicate_counts(db, recent_jobs_rows)
    recent_jobs = [
        job_to_read(job, possible_duplicate_count=dup_counts.get(job.id, 0))
        for job in recent_jobs_rows
    ]

    source_rows = db.execute(
        select(Job.source, func.count())
        .select_from(Job)
        .where(*scope)
        .group_by(Job.source)
        .order_by(func.count().desc())
    ).all()

    latest_run = db.execute(
        select(JobFetchRun).order_by(JobFetchRun.started_at.desc()).limit(1)
    ).scalar_one_or_none()

    today = now.date()
    upcoming_follow_ups = _count(
        db,
        select(func.count())
        .select_from(Application)
        .join(Application.job)
        .where(
            *scope,
            Application.follow_up_date.is_not(None),
            Application.follow_up_date >= today,
            Application.status.in_(list(ACTIVE_APPLICATION_STATUSES)),
        ),
    )

    return DashboardSummary(
        generated_at=now,
        recent_period_hours=recent_period_hours,
        include_test_data=include_test_data,
        total_jobs=total_jobs,
        jobs_discovered_recent=jobs_discovered_recent,
        jobs_published_recent=jobs_published_recent,
        unknown_published_jobs=unknown_published_jobs,
        shortlisted_jobs=shortlisted_jobs,
        applications_total=applications_total,
        applications_submitted=applications_submitted,
        applications_in_progress=applications_in_progress,
        saved_count=counts[ApplicationStatus.SAVED],
        applied_count=counts[ApplicationStatus.APPLIED],
        assessment_count=counts[ApplicationStatus.ASSESSMENT],
        interview_count=counts[ApplicationStatus.INTERVIEW],
        offer_count=counts[ApplicationStatus.OFFER],
        rejected_count=counts[ApplicationStatus.REJECTED],
        withdrawn_count=counts[ApplicationStatus.WITHDRAWN],
        interviews=counts[ApplicationStatus.INTERVIEW],
        offers=counts[ApplicationStatus.OFFER],
        status_breakdown=[
            StatusBreakdownItem(
                status=status,
                label=APPLICATION_STATUS_LABELS[status],
                count=counts[status],
            )
            for status in APPLICATION_STATUS_ORDER
        ],
        source_breakdown=[
            SourceBreakdownItem(
                source=source, label=source_label(source), count=int(count)
            )
            for source, count in source_rows
        ],
        recent_jobs=recent_jobs,
        latest_refresh=fetch_run_to_read(latest_run) if latest_run else None,
        test_data_jobs=test_data_jobs,
        upcoming_follow_ups=upcoming_follow_ups,
    )


def get_activity(
    db: Session,
    *,
    days: int = 14,
    include_test_data: bool = False,
    now: datetime | None = None,
) -> ActivityResponse:
    now = ensure_utc(now) or utcnow()
    today = now.date()
    start_date = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, time.min, tzinfo=now.tzinfo)
    scope = _job_scope(include_test_data)

    buckets = {
        day: ActivityPoint(date=day, jobs_discovered=0, applications_submitted=0)
        for day in date_range_days(today, days)
    }

    discovered_rows = db.execute(
        select(Job.first_seen_at).where(*scope, Job.first_seen_at >= start_dt)
    ).scalars()
    for timestamp in discovered_rows:
        normalized = ensure_utc(timestamp)
        if normalized is not None and normalized.date() in buckets:
            point = buckets[normalized.date()]
            point.jobs_discovered += 1

    application_rows = db.execute(
        select(Application.application_date, Application.created_at)
        .join(Application.job)
        .where(
            *scope,
            Application.status != ApplicationStatus.SAVED,
            or_(
                Application.application_date >= start_date,
                (
                    Application.application_date.is_(None)
                    & (Application.created_at >= start_dt)
                ),
            ),
        )
    ).all()
    for application_date, created_at in application_rows:
        day = application_date
        if day is None:
            normalized = ensure_utc(created_at)
            day = normalized.date() if normalized else None
        if day is not None and day in buckets:
            buckets[day].applications_submitted += 1

    points = [buckets[key] for key in sorted(buckets)]
    return ActivityResponse(
        days=days,
        include_test_data=include_test_data,
        points=points,
        jobs_discovered_total=sum(point.jobs_discovered for point in points),
        applications_submitted_total=sum(
            point.applications_submitted for point in points
        ),
    )
