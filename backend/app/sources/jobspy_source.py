"""LinkedIn / Indeed retrieval through the ``python-jobspy`` package.

Why this module exists
----------------------
LinkedIn has no self-serve job-search API (its Job Posting API is partner-gated
and write-oriented) and Indeed retired its public Publisher/Job Search API, so
the only practical way to pull listings automatically is the boards' public
*guest* search endpoints. ``python-jobspy`` drives exactly those endpoints and
returns a normalized ``pandas`` DataFrame.

Terms-of-service note
---------------------
Scraping is an **opt-in** capability, not a default: nothing is fetched unless the
optional ``python-jobspy`` package is installed (``requirements-scraping.txt``),
``JOBSPY_ENABLED`` is true and the site is listed in ``JOBSPY_SITES``. When it is
enabled the operator accepts that automated access may breach the board's terms
and that the board may throttle or block the requests. JobRadar never attempts
to bypass a block or CAPTCHA: a block is reported as a failed refresh run with
the provider message attached, and nothing is invented to fill the gap.

Design notes
------------
* ``scrape_jobs`` never raises for provider problems in jobspy >= 1.2; failures
  are collected in ``DataFrame.attrs["errors"]``. Those are translated into
  :class:`SourceRequestError` (no rows) or ``FetchResult.errors`` (partial), so a
  blocked scrape can never be mistaken for "no new jobs".
* LinkedIn reports only a **calendar date** (``date_posted``). ``published_at``
  is stored as midnight UTC of that day and flagged
  ``published_at_is_date_only`` so filters and the UI can stay honest.
* Requests are serialized per process with a configurable minimum delay, and the
  number of search terms is capped, to keep traffic polite.
"""

from __future__ import annotations

import math
import re
import threading
import time
from datetime import UTC, date, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.core.constants import ExperienceLevel, SourceAvailability, WorkArrangement
from app.core.logging import get_logger
from app.core.text import clean_text, split_terms
from app.sources.base import (
    FetchResult,
    JobQuery,
    NormalizedJob,
    SourceAdapter,
    SourceUnavailableError,
)

logger = get_logger(__name__)

JOBSPY_PACKAGE = "python-jobspy"
JOBSPY_INSTALL_COMMAND = "pip install -r backend/requirements-scraping.txt"

#: jobspy site key -> JobRadar source key. They currently match by design.
SUPPORTED_SITES: tuple[str, ...] = ("linkedin", "indeed")

_LINKEDIN_JOB_ID = re.compile(r"/jobs/view/(?:[^/?#]*?-)?(\d{5,})")
_INDEED_JOB_ID = re.compile(r"(?:[?&]jk=|/viewjob\?jk=)([0-9A-Za-z]+)")
_NAN_STRINGS = {"nan", "none", "null", "nat", "n/a"}

#: Serializes scraping across request threads and enforces the minimum delay.
_scrape_lock = threading.Lock()
_last_request_at: float = 0.0


def jobspy_available() -> bool:
    """True when the optional scraping package can be imported."""
    try:  # pragma: no cover - depends on the environment
        import jobspy  # noqa: F401
    except Exception:  # pragma: no cover - import guard
        return False
    return True


def _as_text(value: Any) -> str | None:
    """Coerce a pandas cell (including NaN/NaT) to trimmed text or ``None``."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (list, tuple)):
        joined = ", ".join(str(item).strip() for item in value if str(item).strip())
        return joined or None
    text = str(value).strip()
    if not text or text.lower() in _NAN_STRINGS:
        return None
    return text


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _published_at(value: Any) -> tuple[datetime | None, bool]:
    """Return ``(aware UTC timestamp, date_only)`` for a jobspy ``date_posted``."""
    if value is None or value is True or value is False:
        return None, False
    if isinstance(value, float) and math.isnan(value):
        return None, False
    # ``str(pandas.NaT)`` is "NaT" and the generic text guard catches it.
    if isinstance(value, datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return moment.astimezone(UTC), False
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC), True
    text = _as_text(value)
    if text is None:
        return None, False
    try:
        if len(text) == 10:
            day = date.fromisoformat(text)
            return datetime(day.year, day.month, day.day, tzinfo=UTC), True
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:  # pragma: no cover - provider drift
        logger.debug("Unparseable jobspy date_posted: %r", value)
        return None, False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC), False


def _work_arrangement(row: dict[str, Any]) -> WorkArrangement:
    hint = (_as_text(row.get("work_from_home_type")) or "").lower()
    if "hybrid" in hint:
        return WorkArrangement.HYBRID
    if "remote" in hint:
        return WorkArrangement.REMOTE
    if "on-site" in hint or "onsite" in hint or "on site" in hint:
        return WorkArrangement.ONSITE
    # ``is_remote`` is only trusted when the provider says yes: a false value does
    # not distinguish office work from hybrid.
    if _as_bool(row.get("is_remote")) is True:
        return WorkArrangement.REMOTE
    return WorkArrangement.UNKNOWN


_LEVEL_MAP: tuple[tuple[tuple[str, ...], ExperienceLevel], ...] = (
    (("internship", "intern"), ExperienceLevel.ENTRY),
    (("entry level", "entry", "junior", "graduate", "trainee"), ExperienceLevel.ENTRY),
    (("associate",), ExperienceLevel.ASSOCIATE),
    (
        ("mid-senior", "mid senior", "mid level", "senior", "director", "executive"),
        ExperienceLevel.MID_SENIOR,
    ),
)


def _experience_level(row: dict[str, Any]) -> ExperienceLevel:
    for column in ("job_level", "experience_range"):
        hint = (_as_text(row.get(column)) or "").lower()
        if not hint:
            continue
        for needles, level in _LEVEL_MAP:
            if any(needle in hint for needle in needles):
                return level
    return ExperienceLevel.UNKNOWN


def _source_job_id(site: str, row: dict[str, Any]) -> str | None:
    explicit = _as_text(row.get("id"))
    if explicit:
        return explicit
    url = _as_text(row.get("job_url")) or ""
    pattern = _LINKEDIN_JOB_ID if site == "linkedin" else _INDEED_JOB_ID
    match = pattern.search(url)
    return match.group(1) if match else None


def row_to_job(row: dict[str, Any]) -> NormalizedJob | None:
    """Map one jobspy row to a :class:`NormalizedJob`, or ``None`` if unusable."""
    title = clean_text(_as_text(row.get("title")), max_length=300)
    company = clean_text(_as_text(row.get("company")), max_length=200)
    job_url = _as_text(row.get("job_url"))
    if not title or not company or not job_url:
        return None

    published_at, date_only = _published_at(row.get("date_posted"))
    return NormalizedJob(
        title=title,
        company_name=company,
        job_url=job_url,
        source_job_id=_source_job_id(str(row.get("site") or ""), row),
        location=clean_text(_as_text(row.get("location")), max_length=250),
        work_arrangement=_work_arrangement(row),
        experience_level=_experience_level(row),
        description=clean_text(_as_text(row.get("description")), max_length=20_000),
        published_at=published_at,
        published_at_is_date_only=date_only,
    )


def _run_scrape(**kwargs: Any) -> Any:  # pragma: no cover - imports the network stack
    """Indirection so tests can inject a DataFrame without touching the network."""
    from jobspy import scrape_jobs

    return scrape_jobs(**kwargs)


def _respect_delay(delay_seconds: float) -> None:
    """Sleep so consecutive provider calls are at least ``delay_seconds`` apart."""
    global _last_request_at
    if delay_seconds <= 0:
        _last_request_at = time.monotonic()
        return
    waited = time.monotonic() - _last_request_at
    if _last_request_at and waited < delay_seconds:
        time.sleep(delay_seconds - waited)
    _last_request_at = time.monotonic()


class JobSpySourceAdapter(SourceAdapter):
    """Base adapter that funnels one board through ``jobspy.scrape_jobs``."""

    site: str = "linkedin"
    max_results_floor = 1
    #: LinkedIn/Indeed answer with a US-wide feed when nothing is specified.
    requires_search_scope = True

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # -- availability -----------------------------------------------------
    @property
    def _site_enabled(self) -> bool:
        return self.site in (self.settings.jobspy_sites or [])

    @property
    def availability(self) -> SourceAvailability:  # type: ignore[override]
        if not self.settings.jobspy_enabled or not self._site_enabled:
            return SourceAvailability.NOT_CONFIGURED
        if not jobspy_available():
            return SourceAvailability.UNAVAILABLE
        return SourceAvailability.AVAILABLE

    @property
    def can_refresh(self) -> bool:
        return self.supports_refresh and self.availability is SourceAvailability.AVAILABLE

    @property
    def availability_reason(self) -> str | None:  # type: ignore[override]
        if not self.settings.jobspy_enabled:
            return (
                "Scraping is switched off (JOBSPY_ENABLED=false). JobRadar will not "
                "contact the board. Set JOBSPY_ENABLED=true to opt in."
            )
        if not self._site_enabled:
            return (
                f"{self.name} is not in JOBSPY_SITES (currently: "
                f"{', '.join(self.settings.jobspy_sites) or 'empty'}). Add it there "
                "to scrape this board. Scraping is opt-in because it may breach "
                "the board's terms of service."
            )
        if not jobspy_available():
            return (
                f"The optional '{JOBSPY_PACKAGE}' package is not installed, so "
                f"{self.name} cannot be scraped. Install it with: "
                f"{JOBSPY_INSTALL_COMMAND}"
            )
        return (
            "Enabled through python-jobspy, which reads the board's public guest "
            "search pages. Automated access may breach the board's terms of "
            "service and can be throttled or blocked at any time; JobRadar never "
            "bypasses a block. Keep refreshes manual and infrequent."
        )

    @property
    def setup_command(self) -> str | None:  # type: ignore[override]
        if self.availability is SourceAvailability.AVAILABLE:
            return None
        if not jobspy_available():
            return JOBSPY_INSTALL_COMMAND
        if not self.settings.jobspy_enabled:
            return "set JOBSPY_ENABLED=true"
        if not self._site_enabled:
            sites = ", ".join([*self.settings.jobspy_sites, self.site])
            return f"set JOBSPY_SITES={sites}"
        return None

    # -- retrieval --------------------------------------------------------
    def _search_terms(self, query: JobQuery) -> list[str | None]:
        terms = split_terms(
            [*query.titles, *query.keywords],
            max_terms=max(1, self.settings.jobspy_max_search_terms),
        )
        return terms or [None]

    def fetch(self, query: JobQuery) -> FetchResult:
        if self.availability is not SourceAvailability.AVAILABLE:
            raise SourceUnavailableError(
                self.availability_reason or f"{self.name} is unavailable."
            )

        limit = max(self.max_results_floor, min(query.limit, self.settings.jobspy_results_wanted))
        terms = self._search_terms(query)
        result = FetchResult(applied_terms=[term for term in terms if term])
        seen: set[str] = set()
        if terms == [None]:
            result.warnings.append(
                f"No search terms were configured, so {self.name} was queried without "
                "keywords. Add job titles in Search Settings (or type them on the "
                "Discover page) and refresh again for relevant results."
            )
        if not query.location:
            result.warnings.append(
                f"No location was configured, so {self.name} searched every location. "
                "Set a location such as 'Karachi, Pakistan' for local results."
            )

        for index, term in enumerate(terms):
            page = self._scrape_once(
                term=term,
                location=query.location,
                hours_old=query.max_age_hours,
                limit=limit,
                delay=self.settings.jobspy_request_delay_seconds if index else 0.0,
                result=result,
            )
            result.pages_fetched += 1
            for raw in page:
                job = row_to_job({**raw, "site": self.site})
                if job is None:
                    result.warnings.append(
                        "Skipped a listing without a usable title, company or URL."
                    )
                    continue
                key = (job.source_job_id or job.job_url).lower()
                if key in seen:
                    continue
                seen.add(key)
                result.jobs.append(job)

        if not result.jobs and not result.errors:
            label = f" for {term!r}" if term else ""
            result.warnings.append(
                f"{self.name} returned no listings{label} within the requested window. "
                "This can also indicate throttling — check the board manually."
            )
        return result

    def _scrape_once(
        self,
        *,
        term: str | None,
        location: str | None,
        hours_old: int | None,
        limit: int,
        delay: float,
        result: FetchResult,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "site_name": [self.site],
            "search_term": term,
            "location": location or None,
            "results_wanted": limit,
            "hours_old": hours_old,
            "country_indeed": self.settings.jobspy_country,
            "verbose": self.settings.jobspy_verbose,
            "description_format": "markdown",
            "fetch_description": self.settings.jobspy_fetch_description,
        }
        if self.settings.jobspy_proxies:
            kwargs["proxies"] = list(self.settings.jobspy_proxies)

        with _scrape_lock:
            _respect_delay(delay)
            try:
                frame = _run_scrape(**kwargs)
            except Exception as exc:  # network stack, proxies, bad arguments
                message = f"{self.name} request failed: {exc}"
                logger.warning(message)
                result.errors.append(message)
                return []

        error = self._provider_error(frame)
        if error:
            message = f"{self.name} reported an error: {error}"
            logger.warning(message)
            result.errors.append(message)
            return []

        warnings = self._provider_warnings(frame)
        result.warnings.extend(warnings)
        return self._rows(frame)

    @staticmethod
    def _attrs(frame: Any) -> dict[str, Any]:
        attrs = getattr(frame, "attrs", None)
        return attrs if isinstance(attrs, dict) else {}

    def _provider_error(self, frame: Any) -> str | None:
        errors = self._attrs(frame).get("errors") or {}
        if not isinstance(errors, dict):
            return _as_text(errors)
        message = errors.get(self.site)
        if message is None and errors:
            message = next(iter(errors.values()))
        return _as_text(message)

    def _provider_warnings(self, frame: Any) -> list[str]:
        warnings = self._attrs(frame).get("warnings") or {}
        collected: list[str] = []
        if isinstance(warnings, dict):
            for key, value in warnings.items():
                if key != self.site:
                    continue
                values = value if isinstance(value, (list, tuple)) else [value]
                collected.extend(text for text in (_as_text(v) for v in values) if text)
        return collected

    @staticmethod
    def _rows(frame: Any) -> list[dict[str, Any]]:
        if frame is None:
            return []
        records = getattr(frame, "to_dict", None)
        if callable(records):
            try:
                rows = frame.to_dict("records")
            except TypeError:  # pragma: no cover - minimal duck-typed frame
                rows = frame.to_dict()
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        if isinstance(frame, list):  # pragma: no cover - defensive
            return [row for row in frame if isinstance(row, dict)]
        return []
