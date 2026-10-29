# Job sources: access assessment and adapter contract

JobRadar is deliberately conservative about automated job retrieval. A provider
is only marked **available** when listings can be fetched through a method the
platform explicitly permits. Providers that cannot be accessed that way are
listed as **unavailable** and are never scraped.

> Assessment performed on 2026-10-29. Platform terms and APIs change; re-check
> before enabling any live integration.

## LinkedIn

* **Official API:** LinkedIn's Job Posting API is part of its partner programs
  (Talent Solutions / Marketing Developer Platform). It is aimed at approved
  partners publishing and syncing *their own* listings, not at third parties
  searching the job catalogue. Access is gated behind a commercial partnership
  application; there is no self-serve key for job search.
  - Sources: [LinkedIn API access overview](https://elfsight.com/blog/linkedin-api-access-and-pricing/),
    [LinkedIn API overview & partner gates](https://bereach.ai/deliverability/linkedin-jobs-api-official-or-unofficial).
* **Scraping:** LinkedIn's User Agreement prohibits automated collection of
  member/job data, and its guest job-search endpoints are unofficial and
  aggressively rate-limited.
* **JobRadar decision:** `app/sources/linkedin.py` is an *unavailable* adapter.
  Refreshes record a skipped run with a human-readable reason. Roles you find
  manually can be recorded with `POST /api/jobs/import` and `source=linkedin`.

## Indeed

* **Official API:** Indeed retired its public Publisher Job Search API and no
  longer issues new Publisher keys; the remaining APIs (Sponsored Jobs, Indeed
  Apply) are employer/ATS partner programs. The legacy Job Search endpoints are
  documented as deprecated.
  - Sources: [Indeed API status](https://rolesapi.com/blog/indeed-api/),
    [Indeed partner program & retired Publisher API](https://apis.io/plans/indeed/indeed-plans-pricing/).
* **Scraping:** Indeed's Terms of Service prohibit automated extraction; its
  pages use bot detection and CAPTCHAs.
* **JobRadar decision:** `app/sources/indeed.py` is an *unavailable* adapter.
  Manual import with `source=indeed` keeps those links in the tracker.

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
* Refreshes update mutable fields (title, company, location, description,
  arrangement, experience level, URL) and `last_seen_at`. `published_at` is
  filled only once — a later feed cannot silently change posting age.
* Shortlist notes/priority and application records live in separate tables and
  are untouched by ingestion.
