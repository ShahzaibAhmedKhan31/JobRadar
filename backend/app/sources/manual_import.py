"""Manual ingest path.

There is no automated retrieval here: the user pastes the details of a listing
they found themselves. Attaching a provider label (LinkedIn/Indeed/other) keeps
source filters useful without claiming those platforms are integrated.
"""

from __future__ import annotations

from app.core.constants import SourceAvailability
from app.sources.base import (
    FetchResult,
    JobQuery,
    SourceAdapter,
    SourceUnavailableError,
)

#: Sources a manually pasted listing can be attributed to.
MANUAL_IMPORT_SOURCES: tuple[str, ...] = ("manual_import", "linkedin", "indeed", "other")


class ManualImportSourceAdapter(SourceAdapter):
    key = "manual_import"
    name = "Manual import"
    description = (
        "Record a listing you found yourself by pasting its details. "
        "No automated retrieval."
    )
    availability = SourceAvailability.AVAILABLE
    supports_refresh = False
    is_test_data = False
    docs_url = "docs/job-sources.md#manual-import"

    def fetch(self, query: JobQuery) -> FetchResult:
        raise SourceUnavailableError(
            "Manual import does not fetch listings. Use POST /api/jobs/import instead."
        )
