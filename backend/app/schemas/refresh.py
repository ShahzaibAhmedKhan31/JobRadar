"""Source refresh schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ExperienceLevel, FetchRunStatus, RefreshTrigger, WorkArrangement
from app.core.time import ensure_utc
from app.models.fetch_run import JobFetchRun
from app.sources.labels import source_label


class RefreshRequest(BaseModel):
    """Optional hints so providers fetch listings relevant to the user."""

    model_config = ConfigDict(extra="forbid")

    sources: list[str] | None = Field(default=None, max_length=20)
    titles: list[str] = Field(default_factory=list, max_length=10)
    keywords: list[str] = Field(default_factory=list, max_length=10)
    location: str | None = Field(default=None, max_length=200)
    max_age_hours: int | None = Field(default=None, ge=1, le=720)
    work_arrangement: WorkArrangement | None = None
    experience_level: ExperienceLevel | None = None
    limit: int | None = Field(default=None, ge=1, le=2000)


class AppliedQuery(BaseModel):
    """The search actually sent to the providers for this refresh.

    Echoing it back makes "why did nothing come back?" answerable: a scrape with
    no terms or no location is a completely different request from a targeted one.
    """

    terms: list[str] = Field(default_factory=list)
    location: str | None = None
    max_age_hours: int | None = None
    limit: int = 0
    sources: list[str] = Field(default_factory=list)

    @property
    def has_terms(self) -> bool:
        return bool(self.terms)

    def summary(self) -> str:
        parts: list[str] = []
        if self.terms:
            quoted = ", ".join(f'"{term}"' for term in self.terms[:4])
            if len(self.terms) > 4:
                quoted += f" +{len(self.terms) - 4} more"
            parts.append(f"terms {quoted}")
        else:
            parts.append("no search terms (unfiltered feed)")
        if self.location:
            parts.append(f"in {self.location}")
        else:
            parts.append("any location")
        if self.max_age_hours:
            parts.append(f"last {self.max_age_hours}h")
        return " · ".join(parts)


class FetchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    source_label: str
    trigger: RefreshTrigger
    status: FetchRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    fetched_jobs_count: int
    new_jobs_count: int
    updated_jobs_count: int
    unchanged_jobs_count: int
    error_message: str | None = None


def fetch_run_to_read(run: JobFetchRun, *, warnings: list[str] | None = None) -> FetchRunRead:
    started = ensure_utc(run.started_at)
    finished = ensure_utc(run.finished_at)
    duration = None
    if started and finished:
        duration = round(max(0.0, (finished - started).total_seconds()), 2)
    return FetchRunRead(
        id=run.id,
        source=run.source,
        source_label=source_label(run.source),
        trigger=run.trigger,
        status=run.status,
        started_at=started,
        finished_at=finished,
        duration_seconds=duration,
        fetched_jobs_count=run.fetched_jobs_count,
        new_jobs_count=run.new_jobs_count,
        updated_jobs_count=run.updated_jobs_count,
        unchanged_jobs_count=run.unchanged_jobs_count,
        error_message=run.error_message,
    )


class RefreshSourceResult(FetchRunRead):
    warnings: list[str] = Field(default_factory=list)


class RefreshResponse(BaseModel):
    runs: list[RefreshSourceResult]
    new_jobs: int
    updated_jobs: int
    message: str
    #: What was actually asked of the providers (None when nothing was attempted).
    applied_query: AppliedQuery | None = None
