"""Source-adapter contract.

Every job platform integration implements :class:`SourceAdapter`. The rest of the
application only understands :class:`NormalizedJob`, so adding a provider never
requires touching the API, database or UI layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.core.constants import ExperienceLevel, SourceAvailability, WorkArrangement
from app.core.errors import AppError
from app.core.time import ensure_utc


class SourceUnavailableError(AppError):
    """The provider cannot be accessed through an authorized method."""

    status_code = 409
    code = "source_unavailable"


class SourceRequestError(AppError):
    """The provider failed while retrieving listings (network, auth, rate limit)."""

    status_code = 502
    code = "source_request_failed"


@dataclass(frozen=True, slots=True)
class JobQuery:
    """Search criteria forwarded to a provider.

    Providers may ignore criteria they cannot express; results are re-filtered
    against the database afterwards, so this is only a fetch hint.
    """

    titles: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    #: Single location (kept for callers that only ever pass one).
    location: str | None = None
    #: Additional locations. Every place is searched separately by providers
    #: that accept one location per request, so "Karachi, Pakistan" and
    #: "Islamabad, Pakistan" are two searches, not one long string.
    locations: tuple[str, ...] = ()
    max_age_hours: int | None = None
    limit: int = 100

    def keywords_for_provider(self) -> list[str]:
        return [term for term in (*self.titles, *self.keywords) if term.strip()][:10]

    def resolved_locations(self) -> tuple[str, ...]:
        """Every distinct place to search, ``location`` first."""
        from app.core.text import split_locations

        return tuple(split_locations([self.location, *self.locations], max_locations=10))


@dataclass(slots=True)
class NormalizedJob:
    """Provider-agnostic listing payload.

    ``published_at`` must be the *source* publication timestamp, never the time
    we discovered the listing. Use ``None`` when the provider does not expose it.
    """

    title: str
    company_name: str
    job_url: str
    source_job_id: str | None = None
    location: str | None = None
    work_arrangement: WorkArrangement = WorkArrangement.UNKNOWN
    experience_level: ExperienceLevel = ExperienceLevel.UNKNOWN
    description: str | None = None
    published_at: datetime | None = None
    #: True when the provider only exposes a calendar date (e.g. LinkedIn's
    #: "posted 2 days ago"). ``published_at`` is then midnight UTC of that day
    #: and freshness filters treat the whole day as inside the window.
    published_at_is_date_only: bool = False

    def __post_init__(self) -> None:
        self.published_at = ensure_utc(self.published_at)
        if self.published_at is None:
            self.published_at_is_date_only = False

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> NormalizedJob:
        def _enum(value: object, enum_cls: type) -> object:
            if value in (None, ""):
                return enum_cls.UNKNOWN
            return enum_cls(str(value))

        return cls(
            title=str(data.get("title") or ""),
            company_name=str(data.get("company_name") or ""),
            job_url=str(data.get("job_url") or ""),
            source_job_id=(
                str(data["source_job_id"]) if data.get("source_job_id") else None
            ),
            location=str(data["location"]) if data.get("location") else None,
            work_arrangement=_enum(data.get("work_arrangement"), WorkArrangement),
            experience_level=_enum(data.get("experience_level"), ExperienceLevel),
            description=str(data["description"]) if data.get("description") else None,
            published_at=ensure_utc(
                data.get("published_at")  # type: ignore[arg-type]
                if isinstance(data.get("published_at"), datetime)
                else None
            ),
            published_at_is_date_only=bool(data.get("published_at_is_date_only")),
        )


@dataclass(slots=True)
class FetchResult:
    """Outcome of one provider retrieval."""

    jobs: list[NormalizedJob] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pages_fetched: int = 0
    #: Retrieval problems reported by the provider (not row-level rejects).
    errors: list[str] = field(default_factory=list)
    #: Search terms the provider was actually queried with (may be fewer than
    #: requested when a cap applies), for accurate reporting upstream.
    applied_terms: list[str] = field(default_factory=list)
    #: Locations the provider was actually queried with.
    applied_locations: list[str] = field(default_factory=list)

    def __len__(self) -> int:  # pragma: no cover - convenience
        return len(self.jobs)


class SourceAdapter(ABC):
    """Base class for job providers."""

    key: str
    name: str
    description: str
    availability: SourceAvailability = SourceAvailability.AVAILABLE
    availability_reason: str | None = None
    supports_refresh: bool = True
    is_test_data: bool = False
    #: True when the provider returns an arbitrary feed unless it is given a
    #: location or keywords, so a refresh must never run completely unscoped.
    requires_search_scope: bool = False
    docs_url: str | None = None
    #: Environment variables a live integration would need.
    required_config: tuple[str, ...] = ()
    #: Shell command that enables this adapter (shown in the UI when it is off).
    setup_command: str | None = None

    @property
    def can_refresh(self) -> bool:
        return self.supports_refresh and self.availability is SourceAvailability.AVAILABLE

    @abstractmethod
    def fetch(self, query: JobQuery) -> FetchResult:
        """Retrieve listings from the provider.

        Implementations are responsible for pagination, rate limiting and
        translating provider errors into :class:`SourceRequestError`.
        """

    def describe(self) -> dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "availability": self.availability,
            "availability_reason": self.availability_reason,
            "supports_refresh": self.supports_refresh,
            "can_refresh": self.can_refresh,
            "is_test_data": self.is_test_data,
            "docs_url": self.docs_url,
            "required_config": list(self.required_config),
            "setup_command": self.setup_command,
        }
