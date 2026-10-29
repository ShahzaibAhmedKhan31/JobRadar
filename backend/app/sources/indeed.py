"""Indeed source placeholder.

Research summary (see ``docs/job-sources.md``): Indeed retired its public
Publisher Job Search API and no longer issues new keys; the remaining APIs are
employer/ATS partner programs. Scraping breaches Indeed's Terms of Service, so
this adapter is intentionally unavailable.
"""

from __future__ import annotations

from app.core.constants import SourceAvailability
from app.sources.base import (
    FetchResult,
    JobQuery,
    SourceAdapter,
    SourceUnavailableError,
)


class IndeedSourceAdapter(SourceAdapter):
    key = "indeed"
    name = "Indeed"
    description = (
        "Indeed's public job-search API is retired. "
        "Automatic import is disabled."
    )
    availability = SourceAvailability.UNAVAILABLE
    availability_reason = (
        "Indeed retired its Publisher Job Search API and does not issue new "
        "keys; remaining APIs are partner-gated employer tools. Scraping "
        "breaches Indeed's Terms of Service, so JobRadar does not automate it. "
        "Use 'Import a job link' to record Indeed roles you find manually."
    )
    supports_refresh = False
    is_test_data = False
    docs_url = "docs/job-sources.md#indeed"

    def fetch(self, query: JobQuery) -> FetchResult:  # pragma: no cover - guarded
        raise SourceUnavailableError(self.availability_reason or "Indeed is unavailable.")
