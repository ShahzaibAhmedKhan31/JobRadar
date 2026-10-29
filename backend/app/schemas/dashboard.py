"""Dashboard schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.core.constants import ApplicationStatus
from app.schemas.job import JobRead
from app.schemas.refresh import FetchRunRead


class StatusBreakdownItem(BaseModel):
    status: ApplicationStatus
    label: str
    count: int


class SourceBreakdownItem(BaseModel):
    source: str
    label: str
    count: int


class DashboardSummary(BaseModel):
    generated_at: datetime
    recent_period_hours: int
    include_test_data: bool
    total_jobs: int
    jobs_discovered_recent: int
    jobs_published_recent: int
    unknown_published_jobs: int
    shortlisted_jobs: int
    applications_total: int
    applications_submitted: int
    applications_in_progress: int
    saved_count: int
    applied_count: int
    assessment_count: int
    interview_count: int
    offer_count: int
    rejected_count: int
    withdrawn_count: int
    interviews: int
    offers: int
    status_breakdown: list[StatusBreakdownItem]
    source_breakdown: list[SourceBreakdownItem]
    recent_jobs: list[JobRead]
    latest_refresh: FetchRunRead | None = None
    test_data_jobs: int
    upcoming_follow_ups: int


class ActivityPoint(BaseModel):
    date: date
    jobs_discovered: int
    applications_submitted: int


class ActivityResponse(BaseModel):
    days: int
    include_test_data: bool
    points: list[ActivityPoint]
    jobs_discovered_total: int
    applications_submitted_total: int
