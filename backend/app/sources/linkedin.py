"""LinkedIn source placeholder.

Research summary (see ``docs/job-sources.md``): LinkedIn exposes no self-serve
job *search* API. Its Job Posting API is partner-gated and write-oriented
(publishing your own listings). Automated scraping is prohibited by LinkedIn's
User Agreement. This adapter therefore reports itself as unavailable instead of
pretending to work or silently scraping.
"""

from __future__ import annotations

from app.core.constants import SourceAvailability
from app.sources.base import (
    FetchResult,
    JobQuery,
    SourceAdapter,
    SourceUnavailableError,
)


class LinkedInSourceAdapter(SourceAdapter):
    key = "linkedin"
    name = "LinkedIn"
    description = (
        "No authorized public job-search API exists for LinkedIn. "
        "Automatic import is disabled."
    )
    availability = SourceAvailability.UNAVAILABLE
    availability_reason = (
        "LinkedIn offers no self-serve job-search API. Its Job Posting API is "
        "partner-gated and intended for publishing listings, and scraping "
        "violates LinkedIn's User Agreement, so JobRadar does not automate it. "
        "Use 'Import a job link' to record LinkedIn roles you find manually."
    )
    supports_refresh = False
    is_test_data = False
    docs_url = "docs/job-sources.md#linkedin"

    def fetch(self, query: JobQuery) -> FetchResult:  # pragma: no cover - guarded
        raise SourceUnavailableError(self.availability_reason or "LinkedIn is unavailable.")
