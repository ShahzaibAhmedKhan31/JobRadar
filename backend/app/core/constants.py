"""Shared enums and human-readable labels.

These enums are used for both API schemas and database columns so that the
values stored in PostgreSQL are stable and documented.
"""

from __future__ import annotations

from enum import StrEnum


class WorkArrangement(StrEnum):
    """How the job is expected to be performed."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return WORK_ARRANGEMENT_LABELS[self]


WORK_ARRANGEMENT_LABELS: dict[WorkArrangement, str] = {
    WorkArrangement.REMOTE: "Remote",
    WorkArrangement.HYBRID: "Hybrid",
    WorkArrangement.ONSITE: "On-site",
    WorkArrangement.UNKNOWN: "Not specified",
}


class ExperienceLevel(StrEnum):
    """Coarse seniority bucket, normalized across sources."""

    ENTRY = "entry"
    ASSOCIATE = "associate"
    MID_SENIOR = "mid_senior"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return EXPERIENCE_LEVEL_LABELS[self]


EXPERIENCE_LEVEL_LABELS: dict[ExperienceLevel, str] = {
    ExperienceLevel.ENTRY: "Entry level",
    ExperienceLevel.ASSOCIATE: "Associate",
    ExperienceLevel.MID_SENIOR: "Mid-senior",
    ExperienceLevel.UNKNOWN: "Not specified",
}


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def label(self) -> str:
        return PRIORITY_LABELS[self]

    @property
    def rank(self) -> int:
        return {"high": 0, "medium": 1, "low": 2}[self.value]


PRIORITY_LABELS: dict[Priority, str] = {
    Priority.HIGH: "High",
    Priority.MEDIUM: "Medium",
    Priority.LOW: "Low",
}


class ApplicationStatus(StrEnum):
    """Lifecycle of a tracked application.

    ``saved`` only exists so a shortlisted job can be moved into the tracker
    before it is actually submitted. Everything at or past ``applied`` means the
    user confirmed they applied manually.
    """

    SAVED = "saved"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    @property
    def label(self) -> str:
        return APPLICATION_STATUS_LABELS[self]

    @property
    def is_submitted(self) -> bool:
        return self is not ApplicationStatus.SAVED

    @property
    def is_active(self) -> bool:
        """Still in play (not rejected/withdrawn, includes offers)."""
        return self in ACTIVE_APPLICATION_STATUSES


APPLICATION_STATUS_LABELS: dict[ApplicationStatus, str] = {
    ApplicationStatus.SAVED: "Saved",
    ApplicationStatus.APPLIED: "Applied",
    ApplicationStatus.ASSESSMENT: "Assessment",
    ApplicationStatus.INTERVIEW: "Interview",
    ApplicationStatus.OFFER: "Offer",
    ApplicationStatus.REJECTED: "Rejected",
    ApplicationStatus.WITHDRAWN: "Withdrawn",
}

APPLICATION_STATUS_ORDER: tuple[ApplicationStatus, ...] = (
    ApplicationStatus.SAVED,
    ApplicationStatus.APPLIED,
    ApplicationStatus.ASSESSMENT,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
)

#: Statuses that keep a job "in progress" for dashboard purposes.
IN_PROGRESS_APPLICATION_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {ApplicationStatus.ASSESSMENT, ApplicationStatus.INTERVIEW}
)

#: Statuses that count as an active pipeline (not closed).
ACTIVE_APPLICATION_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.SAVED,
        ApplicationStatus.APPLIED,
        ApplicationStatus.ASSESSMENT,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
    }
)


class FetchRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class SourceAvailability(StrEnum):
    """Whether a source can actually retrieve listings today."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


class RefreshTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class SortOption(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    RELEVANT = "relevant"
    COMPANY = "company"
