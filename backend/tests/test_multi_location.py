"""Searching several places at once.

LinkedIn accepts one location per query, so "Karachi, Pakistan plus Islamabad,
Pakistan" has to become two requests. Filtering must then OR the places together,
otherwise the list would hide half of what was just fetched.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from app.core.config import Settings
from app.core.text import split_locations
from app.schemas.refresh import AppliedQuery
from app.services.jobs import JobFilters, list_jobs
from app.services.refresh import LOCATION_REQUEST, resolve_search_scope, run_refresh
from app.services.search_settings import get_or_create_settings
from app.sources import jobspy_source
from app.sources.base import JobQuery
from app.sources.linkedin import LinkedInSourceAdapter
from app.sources.registry import SourceRegistry
from tests.factories import make_job

pytest.importorskip("pandas", reason="python-jobspy (and pandas) is an optional extra")

import pandas as pd


def jobspy_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "jobspy_enabled": True,
        "jobspy_sites": ["linkedin"],
        "jobspy_results_wanted": 25,
        "jobspy_max_search_terms": 2,
        "jobspy_request_delay_seconds": 0,
    }
    base.update(overrides)
    return Settings(**base)


def frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    columns = ["id", "site", "job_url", "title", "company", "location", "date_posted"]
    df = pd.DataFrame(rows, columns=columns)
    df.attrs = {"errors": {}, "warnings": {}}
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
    calls: list[dict[str, Any]] = []
    responses: list[pd.DataFrame] = []

    def fake(**kwargs: Any) -> pd.DataFrame:
        calls.append(kwargs)
        return responses.pop(0) if responses else frame([])

    monkeypatch.setattr(jobspy_source, "_run_scrape", fake)
    return calls, responses


# ------------------------------------------------------------------ parsing


def test_a_comma_belongs_to_the_place():
    assert split_locations(["Karachi, Pakistan"]) == ["Karachi, Pakistan"]


def test_newlines_and_semicolons_separate_places():
    assert split_locations(["Karachi, Pakistan\nIslamabad, Pakistan"]) == [
        "Karachi, Pakistan",
        "Islamabad, Pakistan",
    ]
    assert split_locations(["Karachi, Pakistan; Islamabad, Pakistan"]) == [
        "Karachi, Pakistan",
        "Islamabad, Pakistan",
    ]


def test_the_word_and_separates_two_complete_places():
    assert split_locations(["Karachi, Pakistan and Islamabad, Pakistan"]) == [
        "Karachi, Pakistan",
        "Islamabad, Pakistan",
    ]


def test_a_place_containing_and_stays_one_place():
    assert split_locations(["Trinidad and Tobago"]) == ["Trinidad and Tobago"]


def test_duplicate_places_are_ignored():
    assert split_locations(["Karachi, Pakistan", "karachi, pakistan", " Lahore "]) == [
        "Karachi, Pakistan",
        "Lahore",
    ]


# ------------------------------------------------------------------ filtering


def test_a_job_matches_any_requested_location(db):
    make_job(db, location="Karachi, Sindh, Pakistan", title="Karachi role")
    make_job(db, location="Islamabad, Pakistan", title="Islamabad role")
    make_job(db, location="Dubai, United Arab Emirates", title="Dubai role")

    result = list_jobs(
        db,
        JobFilters(
            locations=["Karachi, Pakistan", "Islamabad, Pakistan"],
            include_test_data=False,
        ),
    )
    assert result.total == 2
    assert {job.title for job in result.jobs} == {"Karachi role", "Islamabad role"}


def test_a_single_box_with_newlines_filters_both_places(db):
    make_job(db, location="Karachi, Pakistan", title="Karachi role")
    make_job(db, location="Islamabad, Pakistan", title="Islamabad role")
    make_job(db, location="Lahore, Pakistan", title="Lahore role")

    result = list_jobs(
        db,
        JobFilters(
            location="Karachi, Pakistan\nIslamabad, Pakistan",
            include_test_data=False,
        ),
    )
    assert result.total == 2


def test_the_api_accepts_repeated_locations(client, db):
    make_job(db, location="Karachi, Pakistan", title="Karachi role")
    make_job(db, location="Islamabad, Pakistan", title="Islamabad role")
    make_job(db, location="Dubai, United Arab Emirates", title="Dubai role")

    payload = client.get(
        "/api/jobs",
        params=[
            ("locations", "Karachi, Pakistan"),
            ("locations", "Islamabad, Pakistan"),
        ],
    ).json()
    assert payload["total"] == 2


# ------------------------------------------------------------------- scraping


def test_one_request_per_term_and_location(db, stub_scrape):
    calls, responses = stub_scrape
    settings = jobspy_settings()
    responses.extend([frame([linkedin_row()]), frame([linkedin_row(id="777", job_url="https://www.linkedin.com/jobs/view/777/", location="Islamabad, Pakistan", title="Platform Engineer")])])

    outcome = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(
            titles=("Backend Engineer",),
            locations=("Karachi, Pakistan", "Islamabad, Pakistan"),
        ),
        registry=SourceRegistry([LinkedInSourceAdapter(settings)]),
        settings=settings,
    )

    assert [call["location"] for call in calls] == ["Karachi, Pakistan", "Islamabad, Pakistan"]
    assert all(call["search_term"] == "Backend Engineer" for call in calls)
    assert outcome.applied_locations == ["Karachi, Pakistan", "Islamabad, Pakistan"]
    assert outcome.new_jobs == 2


def test_the_location_cap_is_enforced_and_reported(db, stub_scrape):
    calls, responses = stub_scrape
    settings = jobspy_settings(jobspy_max_locations=1)
    responses.append(frame([linkedin_row()]))

    outcome = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(
            titles=("Backend Engineer",),
            locations=("Karachi, Pakistan", "Islamabad, Pakistan"),
        ),
        registry=SourceRegistry([LinkedInSourceAdapter(settings)]),
        settings=settings,
    )

    assert [call["location"] for call in calls] == ["Karachi, Pakistan"]
    assert outcome.applied_locations == ["Karachi, Pakistan"]
    assert any("JOBSPY_MAX_LOCATIONS" in warning for warning in outcome.warnings["linkedin"])


def test_saved_settings_can_hold_several_places(db):
    get_or_create_settings(db).default_location = "Karachi, Pakistan; Islamabad, Pakistan"
    db.commit()

    query, source = resolve_search_scope(db, JobQuery(titles=("Backend",)), settings=jobspy_settings())
    assert query.resolved_locations() == ("Karachi, Pakistan", "Islamabad, Pakistan")
    assert source != LOCATION_REQUEST


def test_the_refresh_api_echoes_every_location(client, db):
    payload = client.post(
        "/api/jobs/refresh",
        json={
            "sources": ["fixtures"],
            "titles": ["Backend Engineer"],
            "locations": ["Karachi, Pakistan", "Islamabad, Pakistan"],
        },
    ).json()
    applied = payload["applied_query"]
    assert applied["locations"] == ["Karachi, Pakistan", "Islamabad, Pakistan"]
    assert applied["location"] == "Karachi, Pakistan"
    # The echoes are what the UI shows, so the summary must name both places.
    summary = AppliedQuery(**applied).summary()
    assert "in Karachi, Pakistan, Islamabad, Pakistan" in summary
