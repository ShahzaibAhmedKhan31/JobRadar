# Job sources: access assessment and adapter contract

JobRadar separates two questions: *can* a board be retrieved, and *should* it be?
A provider is only marked **available** when it can actually return listings;
everything is labelled with how it was obtained.

| Source key | Retrieval | Status by default |
|---|---|---|
| `linkedin` | `python-jobspy` guest search (scraping) | **available** when the optional extra is installed, otherwise *unavailable* with install instructions |
| `indeed` | `python-jobspy` guest search (scraping) | **not configured** — add `indeed` to `JOBSPY_SITES` to opt in |
| `manual_import` | user pastes a link | available, no retrieval |
| `fixtures` | bundled synthetic JSON | available, always flagged as test data |

> Assessment performed on 2026-10-29, scraping integration added 2026-10-31.
> Platform terms and endpoints change; re-check before relying on a connector.

## LinkedIn

* **Official API:** LinkedIn's Job Posting API is part of its partner programs
  (Talent Solutions / Marketing Developer Platform). It is aimed at approved
  partners publishing and syncing *their own* listings, not at third parties
  searching the job catalogue. Access is gated behind a commercial partnership
  application; there is no self-serve key for job search.
  - Sources: [LinkedIn API access overview](https://elfsight.com/blog/linkedin-api-access-and-pricing/),
    [LinkedIn API overview & partner gates](https://bereach.ai/deliverability/linkedin-jobs-api-official-or-unofficial).
* **Scraping:** LinkedIn's User Agreement prohibits automated collection of
  member/job data, and its guest job-search endpoints (`/jobs-guest/jobs/api/`)
  are unofficial and aggressively rate-limited. They are the *only* automated
  path that exists.
* **JobRadar decision:** `app/sources/linkedin.py` implements that path through
  [`python-jobspy`](https://pypi.org/project/python-jobspy/), which reads the
  public guest search page. It is **opt-in** and clearly labelled:

  - `pip install -r backend/requirements-scraping.txt` adds the extra.
  - `JOBSPY_SITES` must list `linkedin`; `JOBSPY_ENABLED=false` is a hard
    kill switch. With the package missing, the adapter reports *unavailable* and
    shows the install command instead of pretending to work.
  - One request per saved search term (max `JOBSPY_MAX_SEARCH_TERMS`, default 2)
    with `JOBSPY_REQUEST_DELAY_SECONDS` (default 2s) between calls, and at most
    `JOBSPY_RESULTS_WANTED` (default 25) listings per term.
  - Every request is recorded in refresh history. A throttle, block, CAPTCHA or
    empty page is stored as `failed`/`partial` **with the provider message** —
    never as a silent success, and never padded with invented listings.
  - LinkedIn exposes only the posting **date**; `published_at` is stored at
    midnight UTC with `published_at_is_date_only = true`, and freshness filters
    treat the whole day as inside the window.

  Enabling it is the operator's decision: automated access may breach LinkedIn's
  User Agreement and the account/IP behind it can be blocked. JobRadar does not
  rotate identities to evade a block.

## Indeed

* **Official API:** Indeed retired its public Publisher Job Search API and no
  longer issues new Publisher keys; the remaining APIs (Sponsored Jobs, Indeed
  Apply) are employer/ATS partner programs. The legacy Job Search endpoints are
  documented as deprecated.
  - Sources: [Indeed API status](https://rolesapi.com/blog/indeed-api/),
    [Indeed partner program & retired Publisher API](https://apis.io/plans/indeed/indeed-plans-pricing/).
* **Scraping:** Indeed's Terms of Service prohibit automated extraction; its
  pages use bot detection and CAPTCHAs.
* **JobRadar decision:** `app/sources/indeed.py` shares the jobspy adapter but is
  **not configured by default** — add `indeed` to `JOBSPY_SITES` to opt in. The
  same guard-rails as LinkedIn apply (opt-in, delayed, capped, failures
  reported). `JOBSPY_COUNTRY` only matters for Indeed.

## Sample data provider (available, flagged as test data)

`app/sources/fixtures.py` loads `app/sources/fixtures/jobs.json`, a set of 26
fictional listings (companies, URLs and descriptions are invented). Every row is
stored with `is_test_data = true`:

* Dashboard metrics exclude these rows unless `include_test_data=true`.
* Job results show a “sample” badge.
* The provider exists so the ingestion → filter → shortlist → apply pipeline can
  be exercised without touching a third-party platform.

## Manual import (available, no retrieval)

`POST /api/jobs/import` records a listing the user pasted. It is not an
integration: the user supplies title, company, URL and optional metadata. It is
the authorized path for LinkedIn/Indeed listings until a legitimate feed exists.

## Adding a new provider

1. Create `backend/app/sources/<provider>.py` with a `SourceAdapter` subclass:

   ```python
   from app.sources.base import FetchResult, JobQuery, NormalizedJob, SourceAdapter

   class MyProviderAdapter(SourceAdapter):
       key = "my_provider"
       name = "My Provider"
       description = "Authorized feed explained here."
       availability = SourceAvailability.AVAILABLE
       supports_refresh = True
       required_config = ("MY_PROVIDER_API_KEY",)

       def fetch(self, query: JobQuery) -> FetchResult:
           # Call the authorized API, handle pagination and rate limits,
           # and translate errors into SourceRequestError.
           return FetchResult(jobs=[NormalizedJob(...)])
   ```

2. Register it in `build_registry()` (`backend/app/sources/registry.py`).
3. Add a display label in `backend/app/sources/labels.py`.
4. Read credentials from environment variables only; never expose them to the
   frontend.
5. Store the provider's own publication timestamp in `published_at`; leave it
   `None` when unknown. Never derive it from `first_seen_at`.
6. Provide a stable `source_job_id` whenever possible — dedupe depends on it.

The rest of the application (API, filters, shortlist, dashboard) requires no
changes: it only understands `NormalizedJob` and the shared tables.

## Refresh and dedupe semantics

* A refresh run is recorded per source in `job_fetch_runs` with start/finish,
  status (`running`, `success`, `partial`, `failed`, `skipped`), fetched/new/
  updated/unchanged counts and an error summary.
* An *unavailable or not-configured* source is recorded as `skipped` with the
  reason; it is not reported as a successful import.
* Dedupe keys:
  1. `(source, source_job_id)` — partial unique index when an id exists.
  2. `(source, external_key)` — SHA-256 of the canonical URL plus normalized
     title/company when no id exists.
  3. Same normalized URL within a source is treated as the same listing.
* The same role on two platforms produces two rows with their own URLs; the UI
  flags possible duplicates by normalized company + title and never merges them.
* A provider-reported error with zero usable rows makes the run `failed`; with
  some rows it becomes `partial`. Provider warnings (skipped rows, empty result)
  are attached to the refresh response.
* A refresh with no explicit filters reuses the saved Search Settings (titles,
  keywords, location, posting age), so "Refresh sources" searches for *your*
  roles instead of an unfiltered board.
* Refreshes update mutable fields (title, company, location, description,
  arrangement, experience level, URL) and `last_seen_at`. `published_at` is
  filled only once — a later feed cannot silently change posting age.
* Shortlist notes/priority and application records live in separate tables and
  are untouched by ingestion.
