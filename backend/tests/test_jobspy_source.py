"""Tests for the optional python-jobspy (LinkedIn / Indeed) adapter.

No test touches the network: ``_run_scrape`` is monkeypatched with a real
``pandas.DataFrame`` shaped exactly like jobspy's output (including the
``.attrs`` error/warning channels, which is how jobspy reports failures).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

pytest.importorskip("pandas", reason="python-jobspy (and pandas) is an optional extra")

import pandas as pd

from app.core.config import Settings
from app.core.constants import (
    ExperienceLevel,
    FetchRunStatus,
    SourceAvailability,
    WorkArrangement,
)
from app.core.time import utcnow
from app.models.fetch_run import JobFetchRun
from app.services.refresh import run_refresh
from app.sources import jobspy_source
from app.sources.base import JobQuery, SourceUnavailableError
from app.sources.indeed import IndeedSourceAdapter
from app.sources.linkedin import LinkedInSourceAdapter
from app.sources.registry import build_registry
from tests.factories import make_job


def jobspy_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "jobspy_enabled": True,
        "jobspy_sites": ["linkedin"],
        "jobspy_results_wanted": 25,
        "jobspy_max_search_terms": 2,
        "jobspy_request_delay_seconds": 0,
        "jobspy_verbose": 0,
    }
    base.update(overrides)
    return Settings(**base)


def frame(rows: list[dict[str, Any]], **attrs: Any) -> pd.DataFrame:
    """Build a DataFrame the way jobspy does, with the same attrs channels."""
    columns = ["id", "site", "job_url", "title", "company", "location", "date_posted"]
    df = pd.DataFrame(rows, columns=columns)
    df.attrs = {"errors": attrs.get("errors", {}), "warnings": attrs.get("warnings", {})}
    return df


def linkedin_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": "4123456789",
        "site": "linkedin",
        "job_url": "https://www.linkedin.com/jobs/view/4123456789/",
        "title": "Senior Backend Engineer",
        "company": "Northwind Systems",
        "location": "Karachi, Sindh, Pakistan",
        "date_posted": date.today() - timedelta(days=1),
    }
    row.update(overrides)
    return row


@pytest.fixture()
def stub_scrape(monkeypatch):
    """Replace the network call and record the kwargs it was invoked with."""
    calls: list[dict[str, Any]] = []
    responses: list[pd.DataFrame] = []

    def fake(**kwargs: Any) -> pd.DataFrame:
        calls.append(kwargs)
        return responses.pop(0) if responses else frame([])

    monkeypatch.setattr(jobspy_source, "_run_scrape", fake)
    return calls, responses


# --------------------------------------------------------------------- mapping


def test_row_mapping_normalizes_jobspy_payload():
    adapter = LinkedInSourceAdapter(jobspy_settings())
    row = {
        **linkedin_row(),
        "work_from_home_type": "Hybrid",
        "job_level": "Mid-Senior level",
        "description": "<p>Build APIs</p>",
    }
    job = jobspy_source.row_to_job(row)

    assert job is not None
    assert job.title == "Senior Backend Engineer"
    assert job.company_name == "Northwind Systems"
    assert job.location == "Karachi, Sindh, Pakistan"
    assert job.source_job_id == "4123456789"
    assert job.work_arrangement is WorkArrangement.HYBRID
    assert job.experience_level is ExperienceLevel.MID_SENIOR
    assert job.description == "Build APIs"
    assert job.published_at == datetime.combine(
        date.today() - timedelta(days=1), datetime.min.time(), tzinfo=UTC
    )
    assert job.published_at_is_date_only is True
    assert adapter.key == "linkedin"


@pytest.mark.parametrize(
    ("hint", "expected"),
    [
        ("Remote", WorkArrangement.REMOTE),
        ("Hybrid", WorkArrangement.HYBRID),
        ("On-site", WorkArrangement.ONSITE),
        (None, WorkArrangement.UNKNOWN),
    ],
)
def test_work_arrangement_hints(hint, expected):
    job = jobspy_source.row_to_job({**linkedin_row(), "work_from_home_type": hint})
    assert job is not None
    assert job.work_arrangement is expected


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        ("Internship", ExperienceLevel.ENTRY),
        ("Entry level", ExperienceLevel.ENTRY),
        ("Associate", ExperienceLevel.ASSOCIATE),
        ("Director", ExperienceLevel.MID_SENIOR),
        ("Some new label", ExperienceLevel.UNKNOWN),
    ],
)
def test_experience_level_mapping(level, expected):
    job = jobspy_source.row_to_job({**linkedin_row(), "job_level": level})
    assert job is not None
    assert job.experience_level is expected


def test_exact_timestamp_stays_precise():
    posted = datetime(2026, 10, 30, 9, 30, tzinfo=UTC)
    job = jobspy_source.row_to_job({**linkedin_row(), "date_posted": posted})
    assert job is not None
    assert job.published_at == posted
    assert job.published_at_is_date_only is False


def test_missing_date_is_unknown_not_guessed():
    job = jobspy_source.row_to_job({**linkedin_row(), "date_posted": None})
    assert job is not None
    assert job.published_at is None
    assert job.published_at_is_date_only is False


def test_nan_date_and_blank_fields_are_tolerated():
    assert jobspy_source.row_to_job({**linkedin_row(), "date_posted": float("nan")}).published_at is None  # type: ignore[union-attr]
    assert jobspy_source.row_to_job({**linkedin_row(), "company": "nan"}) is None
    assert jobspy_source.row_to_job({**linkedin_row(), "title": None}) is None


def test_job_id_falls_back_to_url():
    row = {**linkedin_row(), "id": None, "job_url": "https://www.linkedin.com/jobs/view/senior-engineer-at-acme-4099999999/"}
    job = jobspy_source.row_to_job(row)
    assert job is not None
    assert job.source_job_id == "4099999999"


# ----------------------------------------------------------------- availability


def test_adapter_is_available_when_enabled_and_installed(stub_scrape):
    adapter = LinkedInSourceAdapter(jobspy_settings())
    assert adapter.availability is SourceAvailability.AVAILABLE
    assert adapter.can_refresh is True
    assert adapter.setup_command is None
    assert adapter.availability_reason is not None
    assert "terms of service" in adapter.availability_reason.lower()


def test_disabling_scraping_blocks_the_adapter():
    adapter = LinkedInSourceAdapter(jobspy_settings(jobspy_enabled=False))
    assert adapter.availability is SourceAvailability.NOT_CONFIGURED
    assert adapter.can_refresh is False
    assert "JOBSPY_ENABLED" in (adapter.availability_reason or "")
    with pytest.raises(SourceUnavailableError):
        adapter.fetch(JobQuery())


def test_site_must_be_opted_in():
    adapter = IndeedSourceAdapter(jobspy_settings(jobspy_sites=["linkedin"]))
    assert adapter.availability is SourceAvailability.NOT_CONFIGURED
    assert "JOBSPY_SITES" in (adapter.availability_reason or "")
    assert adapter.setup_command == "set JOBSPY_SITES=linkedin, indeed"

    enabled = IndeedSourceAdapter(jobspy_settings(jobspy_sites=["linkedin", "indeed"]))
    assert enabled.availability is SourceAvailability.AVAILABLE


def test_missing_package_is_reported(monkeypatch):
    monkeypatch.setattr(jobspy_source, "jobspy_available", lambda: False)
    adapter = LinkedInSourceAdapter(jobspy_settings())
    assert adapter.availability is SourceAvailability.UNAVAILABLE
    assert "requirements-scraping.txt" in (adapter.availability_reason or "")
    assert adapter.setup_command == jobspy_source.JOBSPY_INSTALL_COMMAND


# ---------------------------------------------------------------------- fetch


def test_fetch_maps_rows_and_passes_search_hints(stub_scrape):
    calls, responses = stub_scrape
    responses.append(frame([linkedin_row(), linkedin_row(id="2", job_url="https://www.linkedin.com/jobs/view/2/", title="Data Engineer")]))

    adapter = LinkedInSourceAdapter(jobspy_settings())
    result = adapter.fetch(
        JobQuery(titles=("Backend Engineer",), location="Karachi", max_age_hours=48, limit=10)
    )

    assert len(result.jobs) == 2
    assert result.errors == []
    assert result.pages_fetched == 1
    assert calls[0]["site_name"] == ["linkedin"]
    assert calls[0]["search_term"] == "Backend Engineer"
    assert calls[0]["location"] == "Karachi"
    assert calls[0]["hours_old"] == 48
    assert calls[0]["results_wanted"] == 10
    assert calls[0]["description_format"] == "markdown"


def test_fetch_caps_results_and_terms(stub_scrape):
    calls, responses = stub_scrape
    responses.extend([frame([linkedin_row()]), frame([linkedin_row(id="77")])])
    adapter = LinkedInSourceAdapter(
        jobspy_settings(jobspy_max_search_terms=2, jobspy_results_wanted=5)
    )
    result = adapter.fetch(
        JobQuery(titles=("Backend", "Data", "Platform"), keywords=("Python",), limit=200)
    )
    assert len(calls) == 2
    assert [call["search_term"] for call in calls] == ["Backend", "Data"]
    assert all(call["results_wanted"] == 5 for call in calls)
    assert len(result.jobs) == 2


def test_fetch_dedupes_duplicate_rows_across_terms(stub_scrape):
    calls, responses = stub_scrape
    responses.extend([frame([linkedin_row()]), frame([linkedin_row()])])
    adapter = LinkedInSourceAdapter(jobspy_settings(jobspy_max_search_terms=2))
    result = adapter.fetch(JobQuery(titles=("Backend", "Platform")))
    assert len(calls) == 2
    assert len(result.jobs) == 1


def test_provider_error_without_rows_is_recorded(stub_scrape):
    _, responses = stub_scrape
    responses.append(
        frame([], errors={"linkedin": "429 Too Many Requests"})
    )
    result = LinkedInSourceAdapter(jobspy_settings()).fetch(JobQuery(titles=("Backend",)))
    assert result.jobs == []
    assert result.errors and "429" in result.errors[0]


def test_provider_error_with_rows_is_partial(stub_scrape):
    _, responses = stub_scrape
    responses.extend(
        [
            frame([linkedin_row()]),
            frame([], errors={"linkedin": "unexpected page with no jobs (blocked?)"}),
        ]
    )
    adapter = LinkedInSourceAdapter(jobspy_settings(jobspy_max_search_terms=2))
    result = adapter.fetch(JobQuery(titles=("Backend", "Platform")))
    assert len(result.jobs) == 1
    assert result.errors and "blocked" in result.errors[0]


def test_raised_exception_is_converted_to_an_error(stub_scrape, monkeypatch):
    def boom(**_: Any) -> pd.DataFrame:
        raise RuntimeError("connection reset by peer")

    monkeypatch.setattr(jobspy_source, "_run_scrape", boom)
    result = LinkedInSourceAdapter(jobspy_settings()).fetch(JobQuery(titles=("Backend",)))
    assert result.jobs == []
    assert result.errors and "connection reset" in result.errors[0]


def test_empty_result_is_warned_not_silent(stub_scrape):
    _, responses = stub_scrape
    responses.append(frame([]))
    result = LinkedInSourceAdapter(jobspy_settings()).fetch(JobQuery(titles=("Backend",)))
    assert result.jobs == []
    assert result.errors == []
    assert any("no listings" in warning for warning in result.warnings)


def test_rows_without_company_are_skipped_with_a_warning(stub_scrape):
    _, responses = stub_scrape
    responses.append(frame([linkedin_row(), linkedin_row(id="2", company=None)]))
    result = LinkedInSourceAdapter(jobspy_settings()).fetch(JobQuery(titles=("Backend",)))
    assert len(result.jobs) == 1
    assert any("usable title" in warning for warning in result.warnings)


# --------------------------------------------------------------- refresh runs


def test_refresh_records_failed_run_when_scraper_is_blocked(
    db, registry, stub_scrape, monkeypatch
):
    from app.sources.base import FetchResult

    class BlockedAdapter(LinkedInSourceAdapter):
        def fetch(self, query: JobQuery) -> FetchResult:
            return FetchResult(errors=["LinkedIn reported an error: 429 Too Many Requests"])

    settings = jobspy_settings()
    adapter = BlockedAdapter(settings)
    outcome = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(titles=("Backend",)),
        registry=registry.__class__([adapter]),
        settings=settings,
    )
    run = outcome.runs[0]
    assert run.status is FetchRunStatus.FAILED
    assert "429" in (run.error_message or "")
    assert run.new_jobs_count == 0


def test_refresh_ingests_scraped_rows_and_is_idempotent(db, stub_scrape):
    calls, responses = stub_scrape
    settings = jobspy_settings()
    adapter = LinkedInSourceAdapter(settings)
    from app.sources.registry import SourceRegistry

    registry = SourceRegistry([adapter])
    responses.append(frame([linkedin_row(), linkedin_row(id="500", job_url="https://www.linkedin.com/jobs/view/500/", title="Platform Engineer")]))

    first = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(titles=("Backend",)),
        registry=registry,
        settings=settings,
    )
    assert first.runs[0].status is FetchRunStatus.SUCCESS
    assert first.new_jobs == 2

    responses.append(frame([linkedin_row(), linkedin_row(id="500", job_url="https://www.linkedin.com/jobs/view/500/", title="Platform Engineer")]))
    second = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(titles=("Backend",)),
        registry=registry,
        settings=settings,
    )
    assert second.new_jobs == 0
    assert second.runs[0].unchanged_jobs_count == 2
    assert len(calls) == 2


def test_date_only_flag_reaches_the_database(db, stub_scrape):
    _, responses = stub_scrape
    settings = jobspy_settings()
    adapter = LinkedInSourceAdapter(settings)
    from app.sources.registry import SourceRegistry

    responses.append(frame([linkedin_row()]))
    run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(titles=("Backend",)),
        registry=SourceRegistry([adapter]),
        settings=settings,
    )
    from sqlalchemy import select

    from app.models.job import Job

    job = db.execute(select(Job).where(Job.source == "linkedin")).scalar_one()
    assert job.published_at_is_date_only is True
    assert job.published_at is not None
    assert job.published_at.hour == 0


def test_registry_returns_jobspy_adapters_only_when_opted_in():
    registry = build_registry(jobspy_settings(jobspy_sites=["linkedin"]))
    keys = [adapter.key for adapter in registry.refresh_targets(None)]
    assert "linkedin" in keys
    assert "indeed" not in keys
    assert registry.get("linkedin").can_refresh is True
    # An explicit request still resolves, even for a disabled site, so the run
    # history can explain why nothing happened.
    assert [a.key for a in registry.refresh_targets(["indeed"])] == ["indeed"]


def test_fetch_run_row_is_persisted(db, stub_scrape):
    _, responses = stub_scrape
    settings = jobspy_settings()
    responses.append(frame([linkedin_row()]))
    from app.sources.registry import SourceRegistry

    run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(titles=("Backend",)),
        registry=SourceRegistry([LinkedInSourceAdapter(settings)]),
        settings=settings,
    )
    run = db.query(JobFetchRun).one()
    assert run.source == "linkedin"
    assert run.finished_at is not None
    assert run.fetched_jobs_count == 1
    assert (run.finished_at - run.started_at) >= timedelta(0)
    assert utcnow() - run.started_at < timedelta(minutes=5)


# ------------------------------------------------- freshness / precision rules


def test_date_only_jobs_overlap_the_freshness_window(db):
    """A date-only posting stays visible while its calendar day can be fresh."""
    from app.services.jobs import JobFilters, list_jobs

    today = utcnow().date()
    fresh = make_job(
        db,
        published_at=datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=UTC),
        published_at_is_date_only=True,
    )
    stale = make_job(
        db,
        published_at=datetime.combine(today - timedelta(days=4), datetime.min.time(), tzinfo=UTC),
        published_at_is_date_only=True,
    )

    result = list_jobs(db, JobFilters(max_age_hours=24, include_test_data=True))
    ids = {job.id for job in result.jobs}
    assert fresh.id in ids
    assert stale.id not in ids


def test_precise_timestamps_keep_exact_semantics(db):
    from app.services.jobs import JobFilters, list_jobs

    recent = make_job(db, published_at=utcnow() - timedelta(hours=2))
    old = make_job(db, published_at=utcnow() - timedelta(days=3))

    result = list_jobs(db, JobFilters(max_age_hours=24, include_test_data=True))
    ids = {job.id for job in result.jobs}
    assert recent.id in ids
    assert old.id not in ids


def test_dashboard_counts_date_only_jobs_as_recent(db):
    from app.services.dashboard import get_summary

    today = utcnow().date()
    make_job(
        db,
        published_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
        published_at_is_date_only=True,
    )
    summary = get_summary(db, recent_period_hours=24, include_test_data=True)
    assert summary.jobs_published_recent >= 1
    assert summary.unknown_published_jobs == 0


def test_ingestion_upgrades_date_only_to_exact_timestamp(db):
    from app.services.ingestion import upsert_job
    from app.sources.base import NormalizedJob

    day = datetime(2026, 10, 20, tzinfo=UTC)
    first = upsert_job(
        db,
        source="linkedin",
        item=NormalizedJob(
            title="Backend Engineer",
            company_name="Northwind",
            job_url="https://www.linkedin.com/jobs/view/1/",
            source_job_id="1",
            published_at=day,
            published_at_is_date_only=True,
        ),
    )
    assert first.job.published_at_is_date_only is True

    second = upsert_job(
        db,
        source="linkedin",
        item=NormalizedJob(
            title="Backend Engineer",
            company_name="Northwind",
            job_url="https://www.linkedin.com/jobs/view/1/",
            source_job_id="1",
            published_at=day + timedelta(hours=9),
            published_at_is_date_only=False,
        ),
    )
    assert second.job.published_at_is_date_only is False
    assert second.job.published_at.hour == 9


# ------------------------------------------------------- saved search reuse


def test_refresh_uses_saved_search_when_no_hints_given(db):
    from app.services.refresh import apply_saved_search
    from app.services.search_settings import get_or_create_settings

    row = get_or_create_settings(db)
    row.default_titles = "Backend Engineer, Platform Engineer"
    row.default_keywords = "FastAPI, PostgreSQL"
    row.default_location = "Karachi, Pakistan"
    row.default_posting_age_hours = 48
    db.commit()

    resolved = apply_saved_search(db, None)
    assert resolved.titles == ("Backend Engineer", "Platform Engineer")
    assert resolved.keywords == ("FastAPI", "PostgreSQL")
    assert resolved.location == "Karachi, Pakistan"
    assert resolved.max_age_hours == 48


def test_explicit_refresh_hints_win_over_saved_search(db):
    from app.services.refresh import apply_saved_search
    from app.services.search_settings import get_or_create_settings

    row = get_or_create_settings(db)
    row.default_titles = "Backend Engineer"
    row.default_location = "Karachi, Pakistan"
    db.commit()

    resolved = apply_saved_search(
        db, JobQuery(titles=("Data Engineer",), location="Lahore", max_age_hours=6)
    )
    assert resolved.titles == ("Data Engineer",)
    assert resolved.location == "Lahore"
    assert resolved.max_age_hours == 6


# ------------------------------------------------- refresh hints → jobspy args


def test_refresh_payload_hints_reach_the_scraper(db, stub_scrape):
    """Titles/location/window from the request must drive the scrape itself."""
    calls, responses = stub_scrape
    settings = jobspy_settings()
    adapter = LinkedInSourceAdapter(settings)
    from app.services.refresh import run_refresh
    from app.sources.registry import SourceRegistry

    responses.append(frame([linkedin_row()]))
    run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(
            titles=("Software Engineer",), location="Karachi, Pakistan", max_age_hours=24, limit=15
        ),
        registry=SourceRegistry([adapter]),
        settings=settings,
    )

    assert calls[0]["search_term"] == "Software Engineer"
    assert calls[0]["location"] == "Karachi, Pakistan"
    assert calls[0]["hours_old"] == 24
    assert calls[0]["results_wanted"] == 15


def test_empty_hints_fall_back_to_the_configured_country(db, stub_scrape):
    """No title and no location must not mean "scrape a random US feed"."""
    calls, responses = stub_scrape
    settings = jobspy_settings(jobspy_country="pakistan")
    from app.services.refresh import run_refresh
    from app.sources.registry import SourceRegistry

    responses.append(frame([]))
    outcome = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(),
        registry=SourceRegistry([LinkedInSourceAdapter(settings)]),
        settings=settings,
    )
    assert calls[0]["search_term"] is None
    assert calls[0]["location"] == "Pakistan"
    assert outcome.applied_query.location == "Pakistan"
    assert outcome.location_source == "default"
    warnings = outcome.warnings["linkedin"]
    assert any("without keywords" in warning for warning in warnings)
    # The location is no longer empty, so the "searched every location" warning
    # must not appear.
    assert not any("searched every location" in warning for warning in warnings)


def test_refresh_api_echoes_the_applied_query(client):
    """The UI must be able to show what was actually searched."""
    response = client.post(
        "/api/jobs/refresh",
        json={
            "sources": ["fixtures"],
            "titles": ["Software Engineer", "AI Engineer"],
            "location": "Karachi, Pakistan",
            "max_age_hours": 48,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    applied = payload["applied_query"]
    assert applied["terms"] == ["Software Engineer", "AI Engineer"]
    assert applied["location"] == "Karachi, Pakistan"
    assert applied["max_age_hours"] == 48
    assert applied["sources"] == ["fixtures"]


def test_refresh_falls_back_to_saved_search_and_reports_it(client):
    client.put(
        "/api/settings",
        json={
            "default_titles": "Backend Engineer, Platform Engineer",
            "default_location": "Karachi, Pakistan",
            "default_posting_age_hours": 24,
        },
    )
    payload = client.post("/api/jobs/refresh", json={"sources": ["fixtures"]}).json()
    applied = payload["applied_query"]
    assert applied["terms"] == ["Backend Engineer", "Platform Engineer"]
    assert applied["location"] == "Karachi, Pakistan"
    assert applied["max_age_hours"] == 24


def test_empty_refresh_message_names_the_search(client):
    payload = client.post(
        "/api/jobs/refresh",
        json={"sources": ["fixtures"], "titles": ["Quantum Basket Weaver"], "max_age_hours": 1},
    ).json()
    # The sample feed is date-relative, so a 1h window yields nothing; either way
    # the message must say what was searched when nothing new arrives.
    if payload["new_jobs"] == 0:
        assert "Searched" in payload["message"]
        assert "Quantum Basket Weaver" in payload["message"]


def test_applied_terms_report_the_cap_honestly(db, stub_scrape):
    """If a cap trims the search, the API must not claim the missing terms ran."""
    _, responses = stub_scrape
    settings = jobspy_settings(jobspy_max_search_terms=2)
    from app.services.refresh import run_refresh
    from app.sources.registry import SourceRegistry

    responses.extend([frame([linkedin_row()]), frame([])])
    outcome = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(titles=("Software Engineer", "AI Engineer", "Cloud Engineer")),
        registry=SourceRegistry([LinkedInSourceAdapter(settings)]),
        settings=settings,
    )
    assert outcome.applied_terms == ["Software Engineer", "AI Engineer"]


def test_three_terms_are_searched_by_default(db, stub_scrape):
    calls, responses = stub_scrape
    from app.services.refresh import run_refresh
    from app.sources.registry import SourceRegistry

    settings = jobspy_settings(jobspy_max_search_terms=Settings().jobspy_max_search_terms)
    responses.extend([frame([linkedin_row(id="1")]), frame([linkedin_row(id="2")]), frame([])])
    outcome = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(
            titles=("Software Engineer", "AI Engineer", "Cloud Engineer"),
            location="Karachi, Pakistan",
            max_age_hours=24,
        ),
        registry=SourceRegistry([LinkedInSourceAdapter(settings)]),
        settings=settings,
    )
    assert [call["search_term"] for call in calls] == [
        "Software Engineer",
        "AI Engineer",
        "Cloud Engineer",
    ]
    assert all(call["location"] == "Karachi, Pakistan" for call in calls)
    assert all(call["hours_old"] == 24 for call in calls)
    assert outcome.applied_terms == ["Software Engineer", "AI Engineer", "Cloud Engineer"]
