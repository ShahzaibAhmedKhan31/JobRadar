"""A refresh must always search *somewhere*.

LinkedIn answers with a US-wide feed when the search has no location, which is
how unrelated listings end up in a Karachi-focused database. These tests pin the
precedence (request → saved settings → configured default) and the refusal to
scrape when even the default is missing.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.config import Settings
from app.core.errors import BadRequestError
from app.services.refresh import (
    LOCATION_DEFAULT,
    LOCATION_REQUEST,
    LOCATION_SAVED,
    resolve_search_scope,
    run_refresh,
)
from app.services.search_settings import get_or_create_settings
from app.sources import jobspy_source
from app.sources.base import JobQuery
from app.sources.linkedin import LinkedInSourceAdapter
from app.sources.registry import SourceRegistry


def jobspy_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "jobspy_enabled": True,
        "jobspy_sites": ["linkedin"],
        "jobspy_request_delay_seconds": 0,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture()
def scraping_available(monkeypatch):
    """Make ``can_refresh`` deterministic without importing the network stack."""
    monkeypatch.setattr(jobspy_source, "jobspy_available", lambda: True)


def test_the_configured_country_is_the_default_location(db):
    query, source = resolve_search_scope(
        db, JobQuery(), settings=jobspy_settings(jobspy_country="pakistan")
    )
    assert query.location == "Pakistan"
    assert source == LOCATION_DEFAULT


def test_explicit_default_location_beats_the_country(db):
    query, source = resolve_search_scope(
        db,
        JobQuery(),
        settings=jobspy_settings(
            jobspy_country="pakistan", jobspy_default_location="Karachi, Pakistan"
        ),
    )
    assert query.location == "Karachi, Pakistan"
    assert source == LOCATION_DEFAULT


def test_a_requested_location_is_never_overridden(db):
    get_or_create_settings(db).default_location = "Karachi, Pakistan"
    db.commit()

    query, source = resolve_search_scope(
        db,
        JobQuery(titles=("Backend Engineer",), location="Lahore"),
        settings=jobspy_settings(jobspy_default_location="Karachi, Pakistan"),
    )
    assert query.location == "Lahore"
    assert source == LOCATION_REQUEST


def test_saved_settings_win_over_the_configured_default(db):
    get_or_create_settings(db).default_location = "Islamabad, Pakistan"
    db.commit()

    query, source = resolve_search_scope(
        db,
        JobQuery(titles=("Backend Engineer",)),
        settings=jobspy_settings(jobspy_default_location="Karachi, Pakistan"),
    )
    assert query.location == "Islamabad, Pakistan"
    assert source == LOCATION_SAVED


def test_an_unscoped_scrape_is_refused(db, scraping_available):
    settings = jobspy_settings(jobspy_country="", jobspy_default_location="")
    registry = SourceRegistry([LinkedInSourceAdapter(settings)])

    with pytest.raises(BadRequestError) as excinfo:
        run_refresh(
            db,
            requested_sources=["linkedin"],
            query=JobQuery(),
            registry=registry,
            settings=settings,
        )
    assert "location" in str(excinfo.value).lower()


def test_a_title_alone_is_enough_scope(db, scraping_available, monkeypatch):
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        jobspy_source, "_run_scrape", lambda **kwargs: calls.append(kwargs) or []
    )
    settings = jobspy_settings(jobspy_country="", jobspy_default_location="")
    registry = SourceRegistry([LinkedInSourceAdapter(settings)])

    outcome = run_refresh(
        db,
        requested_sources=["linkedin"],
        query=JobQuery(titles=("Backend Engineer",)),
        registry=registry,
        settings=settings,
    )
    assert outcome.applied_query.titles == ("Backend Engineer",)
    assert calls and calls[0]["search_term"] == "Backend Engineer"


def test_the_scope_guard_does_not_block_sources_that_need_no_scope(client):
    """Sample/manual sources are not affected by the LinkedIn-specific guard."""
    response = client.post("/api/jobs/refresh", json={"sources": ["fixtures"]})
    assert response.status_code == 200
    assert "job(s)" in response.json()["message"]
