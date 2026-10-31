"""LinkedIn source adapter backed by ``python-jobspy``.

Access summary (see ``docs/job-sources.md``): LinkedIn has no self-serve job
*search* API — its Job Posting API is partner-gated and write-oriented — so the
only automated path is the public guest search endpoint that
``python-jobspy`` reads. That is scraping: it is opt-in, it may breach LinkedIn's
User Agreement, and it can be throttled or blocked. The adapter advertises that
honestly through ``availability_reason`` and never hides a failure.
"""

from __future__ import annotations

from app.sources.jobspy_source import JOBSPY_PACKAGE, JobSpySourceAdapter


class LinkedInSourceAdapter(JobSpySourceAdapter):
    key = "linkedin"
    site = "linkedin"
    name = "LinkedIn"
    description = (
        "LinkedIn guest job search, retrieved with the optional python-jobspy "
        "package. Opt-in scraping: it may breach LinkedIn's User Agreement and "
        "can be throttled at any time."
    )
    supports_refresh = True
    is_test_data = False
    docs_url = "docs/job-sources.md#linkedin"
    required_config = (JOBSPY_PACKAGE,)
