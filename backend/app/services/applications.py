"""Application tracking operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import ApplicationStatus
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.core.logging import get_logger
from app.core.time import utcnow
from app.models.application import Application
from app.models.job import Job
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.jobs import get_job

logger = get_logger(__name__)


@dataclass(slots=True)
class ApplicationFilters:
    statuses: list[ApplicationStatus] = field(default_factory=list)
    company: str | None = None
    search: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort: str = "newest"  # newest | oldest | updated | company


def list_applications(
    db: Session,
    filters: ApplicationFilters,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Application], int]:
    conditions: list[object] = []
    if filters.statuses:
        conditions.append(Application.status.in_(filters.statuses))
    if filters.company and filters.company.strip():
        conditions.append(
            Application.job.has(
                Job.company_name.icontains(filters.company.strip(), autoescape=True)
            )
        )
    if filters.search and filters.search.strip():
        term = filters.search.strip()
        conditions.append(
            or_(
                Application.job.has(Job.title.icontains(term, autoescape=True)),
                Application.job.has(Job.company_name.icontains(term, autoescape=True)),
                Application.notes.icontains(term, autoescape=True),
                Application.resume_reference.icontains(term, autoescape=True),
            )
        )
    if filters.date_from is not None:
        conditions.append(Application.application_date >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(Application.application_date <= filters.date_to)

    total = db.execute(
        select(func.count()).select_from(Application).where(*conditions)
    ).scalar_one()

    statement = select(Application).where(*conditions)
    if filters.sort == "oldest":
        statement = statement.order_by(
            Application.application_date.asc().nulls_last(), Application.created_at.asc()
        )
    elif filters.sort == "updated":
        statement = statement.order_by(Application.updated_at.desc())
    elif filters.sort == "company":
        statement = statement.join(Application.job).order_by(
            Job.company_name.asc(), Application.updated_at.desc()
        )
    else:
        statement = statement.order_by(
            Application.application_date.desc().nulls_last(),
            Application.created_at.desc(),
        )
    statement = statement.offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(statement).unique().scalars().all())
    return items, total


def get_application(db: Session, application_id: uuid.UUID) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise NotFoundError("Application not found")
    return application


def get_application_for_job(db: Session, job_id: uuid.UUID) -> Application | None:
    return db.execute(
        select(Application).where(Application.job_id == job_id)
    ).scalar_one_or_none()


def _validate_dates(
    application_date: date | None, follow_up_date: date | None
) -> None:
    today = utcnow().date()
    if application_date is not None and (application_date - today).days > 1:
        raise UnprocessableError("Application date cannot be in the future")
    if follow_up_date is not None and (follow_up_date - today).days > 365:
        raise UnprocessableError("Follow-up date must be within the next year")
    if (
        follow_up_date is not None
        and application_date is not None
        and follow_up_date < application_date
    ):
        raise UnprocessableError("Follow-up date cannot be before the application date")


def create_application(db: Session, payload: ApplicationCreate) -> Application:
    job = get_job(db, payload.job_id)
    existing = get_application_for_job(db, job.id)
    if existing is not None:
        raise ConflictError(
            "This job already has a tracking record. Update the existing record instead "
            f"(application id: {existing.id})."
        )

    application_date = payload.application_date
    if application_date is None and payload.status.is_submitted:
        application_date = utcnow().date()
    _validate_dates(application_date, payload.follow_up_date)

    application = Application(
        job_id=job.id,
        status=payload.status,
        application_date=application_date,
        notes=payload.notes,
        follow_up_date=payload.follow_up_date,
        resume_reference=payload.resume_reference,
    )
    db.add(application)
    db.commit()
    db.expire_all()
    return db.execute(
        select(Application).where(Application.id == application.id)
    ).scalar_one()


def update_application(
    db: Session,
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    *,
    provided_fields: set[str],
) -> Application:
    application = get_application(db, application_id)

    new_status = (
        payload.status if "status" in provided_fields and payload.status is not None
        else application.status
    )
    new_application_date = (
        payload.application_date
        if "application_date" in provided_fields
        else application.application_date
    )
    new_follow_up = (
        payload.follow_up_date
        if "follow_up_date" in provided_fields
        else application.follow_up_date
    )

    # Moving a saved record into the submitted pipeline stamps today's date
    # unless the caller explicitly supplied one.
    if (
        new_status.is_submitted
        and new_application_date is None
        and "application_date" not in provided_fields
    ):
        new_application_date = utcnow().date()

    _validate_dates(new_application_date, new_follow_up)

    application.status = new_status
    application.application_date = new_application_date
    application.follow_up_date = new_follow_up
    if "notes" in provided_fields:
        application.notes = payload.notes
    if "resume_reference" in provided_fields:
        application.resume_reference = payload.resume_reference
    application.updated_at = utcnow()

    db.commit()
    db.expire_all()
    return get_application(db, application_id)


def delete_application(db: Session, application_id: uuid.UUID) -> None:
    application = get_application(db, application_id)
    db.delete(application)
    db.commit()
    db.expire_all()


def status_counts(db: Session, *, include_test_data: bool = True) -> dict[ApplicationStatus, int]:
    statement = (
        select(Application.status, func.count())
        .select_from(Application)
        .join(Application.job)
        .group_by(Application.status)
    )
    if not include_test_data:
        statement = statement.where(Job.is_test_data.is_(False))
    rows = db.execute(statement).all()
    counts = dict.fromkeys(ApplicationStatus, 0)
    for status, count in rows:
        counts[status] = count
    return counts
