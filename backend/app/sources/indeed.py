"""Indeed source adapter backed by ``python-jobspy``.

Indeed retired its public Publisher/Job Search API (the old endpoints answer
``410 Gone``) and issues no new keys, so the only automated path is Indeed's
public search pages through ``python-jobspy``. It is disabled by default: add
``indeed`` to ``JOBSPY_SITES`` to opt in. As with LinkedIn, scraping may breach
Indeed's Terms of Service, so availability and throttling are reported instead of
hidden.
"""

from __future__ import annotations

from app.sources.jobspy_source import JOBSPY_PACKAGE, JobSpySourceAdapter


class IndeedSourceAdapter(JobSpySourceAdapter):
    key = "indeed"
    site = "indeed"
    name = "Indeed"
    description = (
        "Indeed search results retrieved with the optional python-jobspy package. "
        "Opt-in scraping; Indeed's official job-search API was retired in 2020."
    )
    supports_refresh = True
    is_test_data = False
    docs_url = "docs/job-sources.md#indeed"
    required_config = (JOBSPY_PACKAGE,)
