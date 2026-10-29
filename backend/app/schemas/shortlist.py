"""Shortlist schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import Priority
from app.core.time import ensure_utc
from app.models.shortlist import ShortlistedJob
from app.schemas.job import JobRead, job_to_read


class ShortlistCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Priority = Priority.MEDIUM
    notes: str | None = Field(default=None, max_length=5000)

    def normalized_notes(self) -> str | None:
        if self.notes is None:
            return None
        cleaned = self.notes.strip()
        return cleaned or None


class ShortlistUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Priority | None = None
    notes: str | None = Field(default=None, max_length=5000)


class ShortlistRead(BaseModel):
    id: uuid.UUID
    job: JobRead
    priority: Priority
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


def shortlist_to_read(entry: ShortlistedJob) -> ShortlistRead:
    return ShortlistRead(
        id=entry.id,
        job=job_to_read(entry.job),
        priority=entry.priority,
        notes=entry.notes,
        created_at=ensure_utc(entry.created_at),
        updated_at=ensure_utc(entry.updated_at),
    )
