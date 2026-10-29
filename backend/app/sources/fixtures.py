"""Development provider backed by clearly-labelled synthetic listings.

Nothing here represents a real opening. Every row imported by this adapter is
flagged ``is_test_data=True`` so dashboard metrics can exclude it.
"""

from __future__ import annotations

import json
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.constants import ExperienceLevel, SourceAvailability, WorkArrangement
from app.core.logging import get_logger
from app.core.time import utcnow
from app.sources.base import FetchResult, JobQuery, NormalizedJob, SourceAdapter

logger = get_logger(__name__)

FIXTURE_FILE = Path(__file__).parent / "fixtures" / "jobs.json"


@lru_cache(maxsize=1)
def load_fixture_payload() -> dict[str, Any]:
    with FIXTURE_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


class FixtureSourceAdapter(SourceAdapter):
    """Returns the bundled sample feed; useful for demos and tests."""

    key = "fixtures"
    name = "Sample job feed"
    description = (
        "Built-in synthetic listings so the pipeline can be exercised without "
        "touching LinkedIn or Indeed. Rows are flagged as test data."
    )
    availability = SourceAvailability.AVAILABLE
    supports_refresh = True
    is_test_data = True
    docs_url = "docs/job-sources.md#sample-data-provider"

    def fetch(self, query: JobQuery) -> FetchResult:
        payload = load_fixture_payload()
        raw_jobs: list[dict[str, Any]] = payload.get("jobs", [])
        limit = max(0, query.limit)
        selected = raw_jobs[:limit]
        warnings: list[str] = []
        if len(raw_jobs) > len(selected):
            warnings.append(
                f"Sample feed truncated to {limit} rows by MAX_REFRESH_JOBS_PER_SOURCE."
            )

        now = utcnow()
        jobs: list[NormalizedJob] = []
        for raw in selected:
            posted_hours_ago = raw.get("posted_hours_ago")
            published_at = (
                now - timedelta(hours=float(posted_hours_ago))
                if posted_hours_ago is not None
                else None
            )
            jobs.append(
                NormalizedJob(
                    source_job_id=raw["source_job_id"],
                    title=raw["title"],
                    company_name=raw["company_name"],
                    job_url=raw["job_url"],
                    location=raw.get("location"),
                    work_arrangement=WorkArrangement(
                        raw.get("work_arrangement") or "unknown"
                    ),
                    experience_level=ExperienceLevel(
                        raw.get("experience_level") or "unknown"
                    ),
                    description=raw.get("description"),
                    published_at=published_at,
                )
            )
        logger.info("Fixture provider produced %s sample listings", len(jobs))
        return FetchResult(jobs=jobs, warnings=warnings, pages_fetched=1)
