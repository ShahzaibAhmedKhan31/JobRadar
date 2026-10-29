"""Job listing schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import ApplicationStatus, ExperienceLevel, Priority, WorkArrangement
from app.core.time import ensure_utc, hours_since, utcnow
from app.core.urls import InvalidJobUrlError, validate_job_url
from app.models.job import Job
from app.schemas.common import Page, ensure_aware
from app.sources.labels import source_label


class ShortlistSummary(BaseModel):
    id: uuid.UUID
    priority: Priority
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationSummary(BaseModel):
    id: uuid.UUID
    status: ApplicationStatus
    application_date: date | None = None
    follow_up_date: date | None = None
    resume_reference: str | None = None
    updated_at: datetime


class DuplicateRef(BaseModel):
    id: uuid.UUID
    source: str
    source_label: str
    title: str
    company_name: str
    job_url: str
    published_at: datetime | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    source_label: str
    source_job_id: str | None = None
    title: str
    company_name: str
    location: str | None = None
    work_arrangement: WorkArrangement
    experience_level: ExperienceLevel
    description_snippet: str | None = None
    job_url: str
    published_at: datetime | None = None
    posting_age_hours: float | None = None
    first_seen_at: datetime
    discovered_age_hours: float
    last_seen_at: datetime
    is_test_data: bool
    is_shortlisted: bool
    shortlist: ShortlistSummary | None = None
    application: ApplicationSummary | None = None
    possible_duplicate_count: int = 0


class JobPage(Page[JobRead]):
    unknown_published_count: int = 0
    include_test_data: bool = True


class JobDetail(JobRead):
    description: str | None = None
    possible_duplicates: list[DuplicateRef] = Field(default_factory=list)


class ManualJobImport(BaseModel):
    """Payload for recording a listing the user found manually."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    company_name: str = Field(min_length=1, max_length=200)
    job_url: str = Field(min_length=1, max_length=2000)
    source: str = Field(default="manual_import", max_length=50)
    source_job_id: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=250)
    work_arrangement: WorkArrangement = WorkArrangement.UNKNOWN
    experience_level: ExperienceLevel = ExperienceLevel.UNKNOWN
    description: str | None = Field(default=None, max_length=20000)
    published_at: datetime | None = None

    @field_validator("title", "company_name", "source")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("job_url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        try:
            return validate_job_url(value)
        except InvalidJobUrlError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("published_at")
    @classmethod
    def _validate_published_at(cls, value: datetime | None) -> datetime | None:
        normalized = ensure_aware(value)
        if normalized is not None and normalized > utcnow().replace(microsecond=0):
            raise ValueError("publication time cannot be in the future")
        return normalized

    @field_validator("location", "description", "source_job_id")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ManualImportResponse(BaseModel):
    job: JobDetail
    created: bool
    message: str


def posting_age_hours(job: Job) -> float | None:
    """Age since the *source* publication time (never from discovery time)."""
    published_at = ensure_utc(job.published_at)
    if published_at is None:
        return None
    return round(max(0.0, hours_since(published_at)), 1)


def job_to_read(
    job: Job,
    *,
    possible_duplicate_count: int = 0,
    include_description: bool = False,
    possible_duplicates: list[Job] | None = None,
) -> JobRead:
    from app.core.text import snippet

    shortlist = job.shortlist_entry
    application = job.application
    payload = {
        "id": job.id,
        "source": job.source,
        "source_label": source_label(job.source),
        "source_job_id": job.source_job_id,
        "title": job.title,
        "company_name": job.company_name,
        "location": job.location,
        "work_arrangement": job.work_arrangement,
        "experience_level": job.experience_level,
        "description_snippet": snippet(job.description, 220),
        "job_url": job.job_url,
        "published_at": ensure_utc(job.published_at),
        "posting_age_hours": posting_age_hours(job),
        "first_seen_at": ensure_utc(job.first_seen_at),
        "discovered_age_hours": round(
            hours_since(ensure_utc(job.first_seen_at) or utcnow()), 1
        ),
        "last_seen_at": ensure_utc(job.last_seen_at),
        "is_test_data": job.is_test_data,
        "is_shortlisted": shortlist is not None,
        "shortlist": (
            ShortlistSummary(
                id=shortlist.id,
                priority=shortlist.priority,
                notes=shortlist.notes,
                created_at=ensure_utc(shortlist.created_at),
                updated_at=ensure_utc(shortlist.updated_at),
            )
            if shortlist is not None
            else None
        ),
        "application": (
            ApplicationSummary(
                id=application.id,
                status=application.status,
                application_date=application.application_date,
                follow_up_date=application.follow_up_date,
                resume_reference=application.resume_reference,
                updated_at=ensure_utc(application.updated_at),
            )
            if application is not None
            else None
        ),
        "possible_duplicate_count": possible_duplicate_count,
    }
    if include_description:
        return JobDetail(
            **payload,
            description=job.description,
            possible_duplicates=[
                DuplicateRef(
                    id=other.id,
                    source=other.source,
                    source_label=source_label(other.source),
                    title=other.title,
                    company_name=other.company_name,
                    job_url=other.job_url,
                    published_at=ensure_utc(other.published_at),
                )
                for other in (possible_duplicates or [])
            ],
        )
    return JobRead(**payload)
