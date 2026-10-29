"""Application tracker schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import ApplicationStatus
from app.core.time import ensure_utc, utcnow
from app.models.application import Application
from app.schemas.job import JobRead, job_to_read

MAX_NOTES_LENGTH = 5000


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID
    status: ApplicationStatus = ApplicationStatus.SAVED
    application_date: date | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    follow_up_date: date | None = None
    resume_reference: str | None = Field(default=None, max_length=255)

    @field_validator("application_date")
    @classmethod
    def _application_date_not_future(cls, value: date | None) -> date | None:
        if value is not None and (value - utcnow().date()).days > 1:
            raise ValueError("application date cannot be in the future")
        return value

    @field_validator("follow_up_date")
    @classmethod
    def _follow_up_within_a_year(cls, value: date | None) -> date | None:
        if value is not None and (value - utcnow().date()).days > 365:
            raise ValueError("follow-up date must be within the next year")
        return value

    @field_validator("notes", "resume_reference")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def _check_dates(self) -> ApplicationCreate:
        if (
            self.follow_up_date is not None
            and self.application_date is not None
            and self.follow_up_date < self.application_date
        ):
            raise ValueError("follow-up date cannot be before the application date")
        return self


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus | None = None
    application_date: date | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    follow_up_date: date | None = None
    resume_reference: str | None = Field(default=None, max_length=255)

    @field_validator("application_date")
    @classmethod
    def _application_date_not_future(cls, value: date | None) -> date | None:
        if value is not None and (value - utcnow().date()).days > 1:
            raise ValueError("application date cannot be in the future")
        return value

    @field_validator("follow_up_date")
    @classmethod
    def _follow_up_within_a_year(cls, value: date | None) -> date | None:
        if value is not None and (value - utcnow().date()).days > 365:
            raise ValueError("follow-up date must be within the next year")
        return value

    @field_validator("notes", "resume_reference")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    job: JobRead
    status: ApplicationStatus
    application_date: date | None = None
    notes: str | None = None
    follow_up_date: date | None = None
    resume_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationStatusColumn(BaseModel):
    status: ApplicationStatus
    label: str
    count: int
    items: list[ApplicationRead]


def application_to_read(application: Application) -> ApplicationRead:
    return ApplicationRead(
        id=application.id,
        job=job_to_read(application.job),
        status=application.status,
        application_date=application.application_date,
        notes=application.notes,
        follow_up_date=application.follow_up_date,
        resume_reference=application.resume_reference,
        created_at=ensure_utc(application.created_at),
        updated_at=ensure_utc(application.updated_at),
    )
