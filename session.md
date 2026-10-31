# session.md — JobRadar working notes & handoff

> Running log of this project: what exists, how to run it, what was decided, and
> what is still open. **Update this file at the end of every work session** so the
> next agent (or human) can continue without re-deriving context.
>
> Last updated: **2026-10-31** · Branch: `arena/199744a1-jobradar` ·
> Stack: Next.js 15 + FastAPI + PostgreSQL 16.
>
> **Current PR:** [#2](https://github.com/ShahzaibAhmedKhan31/JobRadar/pull/2)
> (`arena/199744a1-jobradar` → `main`). The MVP itself is already merged on
> `main` via PR #1. Commits on this branch:
> `1a31385` backend/adapter/docs · `0d9a8e3` frontend · `6feece3` this file.

---

## 1. What JobRadar is

A single-user, local-first job search tool. No auth, no multi-tenancy.

| Area | Route | What it does |
| --- | --- | --- |
| Dashboard | `/` | Metrics from real DB rows: total jobs, published in a selected period (24h/48h/7d/14d/30d), shortlisted, applications submitted, in progress, interviews, offers, status breakdown, activity chart (7/14/30 days), recent jobs, latest refresh, follow-ups |
| Discover jobs | `/discover` | Search stored listings: multiple titles/keywords, location, work arrangement, experience level, sources, posting age (6h/12h/24h/48h/7d, optional “include unknown publication time”), sort newest/oldest/relevant/company; shortlist or track from the card |
| Shortlist | `/shortlist` | Priority (high/medium/low), notes, filters by source/priority/date, move to tracker, remove (confirmed) |
| Applications | `/applications` | Statuses `saved → applied → assessment → interview → offer → rejected/withdrawn`; `application_date`, `note`, `follow_up_date`, `resume_reference`; table **and** Kanban; search + filters |
| Search settings | `/settings` | Saved search defaults, source availability + “how to enable”, scraping guard-rails, refresh history |

Statuses (`APPLICATION_STATUS_LABELS`) and labels for sources live in the
backend; the frontend mirrors them in `frontend/lib/constants.ts`.

Non-negotiables baked into the code:

* Opening a listing **never** marks anything as applied. Applications are only
  created by an explicit user action.
* Sample/demo data is flagged `is_test_data` and excluded from dashboard metrics
  by default.
* A source that cannot run is reported as `skipped`/`failed` **with the reason** —
  never as a successful empty import.

---

## 2. Repository map

```
JobRadar/
├── docker-compose.yml          # PostgreSQL 16 ONLY (app processes run on the host)
├── .env.example                # POSTGRES_DB/USER/PASSWORD/PORT for compose
├── docs/job-sources.md         # access assessment, adapter contract, dedupe rules
├── README.md                   # full Windows/macOS/Linux setup + API + troubleshooting
├── session.md                  # this file
├── scripts/preflight.py        # environment doctor (DB, migrations, ports, deps)
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app factory, lifespan, /health
│   │   ├── api/routes/         # jobs, shortlist, applications, dashboard, settings, sources, health
│   │   ├── core/               # config, constants (enums), errors, logging, text, time, urls
│   │   ├── db/                 # Base, session factory, types (UTCDateTime), startup wait
│   │   ├── models/             # job, shortlist, application, fetch_run, search_settings
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── services/           # jobs, ingestion, refresh, shortlist, applications, dashboard, scheduler
│   │   └── sources/            # base contract, registry, jobspy_source, linkedin, indeed, manual_import, fixtures
│   ├── alembic/                # migrations (head: 868a9d33f328)
│   ├── tests/                  # 121 pytest tests (PostgreSQL by default, SQLite fallback)
│   ├── requirements.txt        # core runtime deps
│   ├── requirements-dev.txt    # + pytest, httpx, ruff
│   └── requirements-scraping.txt  # OPTIONAL: python-jobspy (LinkedIn/Indeed)
└── frontend/
    ├── app/                    # App Router pages + globals.css + not-found/error
    ├── components/             # ui primitives, layout, jobs, shortlist, applications, dashboard
    ├── lib/                    # api client, react-query hooks, constants, utils
    ├── types/index.ts          # shared API types
    └── next.config.ts          # rewrites /api, /health, /docs, /openapi.json → FastAPI
```

---

## 3. Running it

### Windows (PowerShell)

```powershell
git clone https://github.com/ShahzaibAhmedKhan31/JobRadar.git
cd JobRadar
Copy-Item .env.example .env
docker compose up -d postgres            # wait for "healthy"

# backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
pip install -r backend\requirements-scraping.txt   # OPTIONAL: LinkedIn/Indeed
cd backend
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# second terminal: frontend
cd frontend
npm install
npm run dev                              # http://localhost:3000
```

Tests (needs PostgreSQL up; creates/drops tables in `jobradar_test` only):

```powershell
docker exec -it jobradar-postgres createdb -U jobradar jobradar_test   # once
cd backend
pytest -q                                # 121 passed
ruff check app tests
```

### macOS / Linux

Same, with `python3 -m venv .venv`, `source .venv/bin/activate`, and
`cp .env.example .env`.

### Sandbox notes (this environment)

* No Docker: PostgreSQL is started from the `pgserver` bundle —
  `initdb -D /tmp/jr_pg -U jobradar --auth=trust -E UTF8 --locale=C` (the UTF8
  flag matters: an SQL_ASCII cluster makes psycopg return `bytes` and breaks
  SQLAlchemy with a `re.match` TypeError), then
  `postgres -D /tmp/jr_pg -p 5432 -h 127.0.0.1 -k /tmp/jr_pg`.
* `.venv`, `frontend/node_modules`, `.next` and `/tmp` do **not** survive between
  sessions — reinstall (`python3 -m venv .venv && .venv/bin/pip install -r
  backend/requirements-dev.txt && .venv/bin/pip install pgserver python-jobspy`)
  and re-run `npm install` after a restart.
* Egress is limited to PyPI/npm/GitHub. **linkedin.com is not reachable**, so a
  live scrape cannot be validated here (it fails at the TLS layer and is recorded
  as a `failed` run — see §7).

---

## 4. Data model (PostgreSQL)

| Table | Key columns | Notes |
| --- | --- | --- |
| `jobs` | `id` (UUID), `source`, `source_job_id`, `external_key`, `title`, `company_name`, `location`, `work_arrangement`, `experience_level`, `description`, `job_url`, `published_at` (nullable, tz-aware), `published_at_is_date_only`, `first_seen_at`, `last_seen_at`, `is_test_data`, timestamps | Partial unique indexes on `(source, source_job_id)` and `(source, external_key)`; indexes on `published_at`, `first_seen_at`, `(source, published_at)`, `company_name` |
| `shortlisted_jobs` | `id`, `job_id` (unique FK), `priority`, `notes`, timestamps | One shortlist row per job; deleting the job cascades |
| `applications` | `id`, `job_id` (unique FK), `status`, `application_date`, `notes`, `follow_up_date`, `resume_reference`, timestamps | `CHECK follow_up_date >= application_date`; one application per job |
| `job_fetch_runs` | `id`, `source`, `trigger`, `status`, `started_at`, `finished_at`, fetched/new/updated/unchanged counts, `error_message` | Refresh history |
| `search_settings` | singleton row (`id=1`), default titles/keywords/location/arrangement/level/posting age/sources, scheduler toggle + interval | Seeds Discover filters and refresh hints |

Enumerations are `VARCHAR(32)` + `CHECK` constraints, mirrored by `StrEnum`s in
`backend/app/core/constants.py`.

### Timestamp semantics (important)

* All timestamps are **UTC, timezone-aware**. `UTCDateTime` re-attaches UTC after
  a SQLite round-trip.
* `published_at` = when the **source** says the job was posted. It is never
  derived from `first_seen_at`, never overwritten by later refreshes, and stays
  `NULL` when the provider does not say.
* `first_seen_at` = when JobRadar first stored the row. The UI shows both
  (“Posted …” vs “Discovered …”).
* `published_at_is_date_only` = the provider only gave a calendar date
  (LinkedIn). `published_at` is then midnight UTC and freshness filters treat the
  whole day as inside the window (`published_since()` in
  `services/jobs.py`). Cards render “Posted around Xd (date only)”.

---

## 5. API surface

Base prefix `/api`; OpenAPI at `/docs` (proxied by Next as `/docs`).

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | `{status, database, version, environment, time}` |
| GET | `/api/jobs` | `q`, `titles[]`, `keywords[]`, `location`, `work_arrangement`, `experience_level`, `sources[]`, `max_age_hours`, `include_unknown_published`, `shortlisted`, `application_status[]`, `include_test_data`, `sort`, `page`, `page_size` |
| GET | `/api/jobs/{id}` | Detail incl. possible duplicates |
| POST | `/api/jobs/refresh` | `{sources?, titles?, keywords?, location?, max_age_hours?, limit?}` → per-source runs + message |
| GET | `/api/jobs/refresh-history` | `source`, `status`, pagination |
| POST | `/api/jobs/import` | Manual link import; `201` created, `200` if it already exists |
| GET/POST/PATCH/DELETE | `/api/shortlist[/{job_id}]` | Filters: `source`, `priority`, `date_from`, `date_to`, `sort` |
| GET/POST | `/api/applications` | Filters: `status[]`, `company`, `date_from`, `date_to`, pagination |
| GET/PATCH/DELETE | `/api/applications/{id}` | Status transitions; closing statuses clear nothing else |
| GET | `/api/dashboard/summary` | `recent_period_hours`, `include_test_data` |
| GET | `/api/dashboard/activity` | `days` 1–90, `include_test_data` |
| GET/PUT | `/api/settings` | Saved search defaults + scheduler toggle |
| GET | `/api/sources` | Availability, reason, `setup_command`, stored count, last run |

---

## 6. Source adapters

Contract: `backend/app/sources/base.py` (`SourceAdapter.fetch(JobQuery) →
FetchResult`). Everything downstream only understands `NormalizedJob`, so a new
provider never touches the API, DB or UI.

| Key | Adapter | Retrieval | Default state |
| --- | --- | --- | --- |
| `linkedin` | `sources/linkedin.py` → `sources/jobspy_source.py` | `python-jobspy` LinkedIn guest search | available **iff** the extra is installed and `JOBSPY_ENABLED=true` + site listed |
| `indeed` | `sources/indeed.py` → same base | jobspy Indeed search | `not_configured` until `indeed` is added to `JOBSPY_SITES` |
| `manual_import` | `sources/manual_import.py` | user pastes a URL | available, `supports_refresh=false` |
| `fixtures` | `sources/fixtures.py` | bundled `fixtures/jobs.json` (26 synthetic rows) | available, `is_test_data=true` |

### jobspy integration (added 2026-10-31)

* `scrape_jobs(site_name=[site], search_term=…, location=…, results_wanted=…,
  hours_old=…, country_indeed=…, proxies=…, description_format="markdown",
  fetch_description=…)` is called through the indirection
  `jobspy_source._run_scrape(**kwargs)` — tests monkeypatch that name, so **no
  test touches the network**.
* Search terms come from `JobQuery.titles + keywords`, capped by
  `JOBSPY_MAX_SEARCH_TERMS` (default 2). If a refresh request has no hints, the
  saved Search Settings are used (`services/refresh.py::apply_saved_search`).
* One request per term, serialized by a process lock with
  `JOBSPY_REQUEST_DELAY_SECONDS` (default 2s) between calls; `results_wanted` is
  capped by `JOBSPY_RESULTS_WANTED` (default 25) and the request `limit`.
* **jobspy ≥1.2 never raises for provider problems**; failures are reported in
  `DataFrame.attrs["errors"][site]` (warnings in `attrs["warnings"]`). The adapter
  reads those channels: no rows + error → run `failed`; some rows + error → run
  `partial`; rows + warnings → `success` with warnings in the response. A plain
  exception is also caught and stored as the error message.
* Row mapping (`row_to_job`): `title`/`company`/`job_url` are required (rows
  missing any are skipped with a warning); `id` or the id in the URL becomes
  `source_job_id`; `work_from_home_type` maps to remote/hybrid/onsite (a bare
  `is_remote=false` stays `unknown`); `job_level` maps to the four experience
  buckets; `date_posted` is a `datetime.date` → midnight UTC + date-only flag.
* `JOBSPY_ENABLED=false` is a hard kill switch; a missing package yields
  `unavailable` + the exact install command (`setup_command`), surfaced in the UI.

---

## 7. Verified state

Last verified 2026-10-31 on this branch:

| Check | Result |
| --- | --- |
| `pytest -q` (backend) | **121 passed** |
| `ruff check app tests` | clean |
| `alembic check` | “No new upgrade operations detected” (head `868a9d33f328`) |
| `npx tsc --noEmit` | clean |
| `npm run lint` | 0 problems |
| `npm run build` | success — `/`, `/discover`, `/shortlist`, `/applications`, `/settings`, `/_not-found` |
| `scripts/preflight.py` | PASS on all required checks (DB, migrations, ports, deps); FAIL messages verified with an unreachable port and a wrong `DATABASE_URL` |
| Pages through the Next proxy | `/` 200, `/discover` 200, `/shortlist` 200, `/applications` 200, `/settings` 200, unknown route 404, `/docs` 200 |
| `/api/sources` live | `linkedin available` (jobspy installed), `indeed not_configured` + `set JOBSPY_SITES=linkedin, indeed`, `fixtures available` |
| Live jobspy attempt | Real HTTPS request to `www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=…&start=0`; the sandbox proxy closed the TLS connection → run stored as `failed` with the exact provider message (proves the error path, **not** a successful scrape) |
| Date-only round trip | Row with `published_at_is_date_only=true` returned by `/api/jobs`, included in a 24h window despite a 38h-old timestamp |

What was **not** verified: a successful live LinkedIn scrape (no egress from the
build sandbox) and browser-level interaction (no browser in the sandbox — UI was
checked through HTTP + API calls).

---

## 8. Decisions worth keeping

1. **PostgreSQL in Docker only.** Frontend and backend run on the host; no app
   containers, no Redis/Celery/K8s.
2. **Same-origin API.** The browser calls relative `/api/*`; `next.config.ts`
   rewrites to `API_PROXY_TARGET` (default `http://127.0.0.1:8000`). No CORS
   needed in the browser, and preview proxies keep working. `/docs` and
   `/openapi.json` are proxied too.
3. **Scraping is opt-in and honest.** It is a separate requirements file plus
   explicit env flags. Availability, throttling and blocks are always reported;
   no CAPTCHA solving, no proxy rotation for evasion (proxies are passed through
   only if the operator sets `JOBSPY_PROXIES`), no fabricated listings.
4. **Date-only timestamps are first-class** (`published_at_is_date_only`) rather
   than being silently rounded or treated as unknown.
5. **Dedupe**: `(source, source_job_id)` → `(source, external_key)` (SHA-256 of
   canonical URL + normalized title/company) → same normalized URL. Cross-platform
   duplicates are flagged, never merged.
6. **Migrations are the schema source of truth**; `Base.metadata.create_all` is
   only used by tests.
7. **Scheduler** is an asyncio task inside the API process (single user), off by
   default (`SCHEDULED_REFRESH_ENABLED=false`).

---

## 9. Known gaps / good next steps

* **No live LinkedIn validation** in CI or in this sandbox; add a manual smoke
  script or an opt-in `-m live` test once credentials/egress exist.
* **No frontend test suite**; add Playwright for the four main flows.
* **Indeed is opt-in** and untested against the live site (`JOBSPY_SITES`).
* **Scraping fragility**: LinkedIn/Indeed markup changes break jobspy, not our
  code — surface version pinning (`python-jobspy>=1.4,<2.0`) in the changelog.
* **No auth**: do not expose beyond localhost without adding a login.
* **Resume references are names only** (no upload/storage).
* Possible improvements: saved named searches, email-alert ingestion, a
  “new since last visit” counter, drag-and-drop Kanban, response-rate analytics.
* Licensed feed (Adzuna/JSearch/Greenhouse/Lever) behind the existing
  `SourceAdapter` would remove the scraping dependency entirely.

---

## 10. Session log

Newest first. Each entry: date · what changed · files · verification.

### 2026-10-31 (later) — "connection refused" support work

**Symptom reported:** `Failed to proxy http://127.0.0.1:8000/health Error: connect
ECONNREFUSED` in the Next.js log on Windows. The frontend was fine; nothing was
listening on 8000, i.e. uvicorn had exited (or was never started in a second
terminal).

**Added**
* `scripts/preflight.py` — environment doctor. Checks Python version, backend
  imports, `.env` files, database connectivity (with the real URL, password
  masked), Alembic head vs database version, `node`/`node_modules`, port 8000
  (`/health`) and 3000, and the optional jobspy install; every failure prints the
  exact command that fixes it. Exit code 1 when a required check fails.
* `ErrorState` now detects `ApiError` with `status === 0` and renders a
  “Backend not reachable” panel with the uvicorn command and a pointer to the
  preflight script, instead of a generic error.
* README: “First stop: run the preflight doctor” section, a six-cause
  `ECONNREFUSED` checklist, five new troubleshooting rows, and the script in the
  repo map / quick start.

**Changed**
* `lib/api.ts` — refused-connection message now also mentions `API_PROXY_TARGET`.
* Sidebar API widget shows `Run: uvicorn app.main:app --port 8000`.

**Verification** — `preflight.py` passes against the live local stack; simulated
failures (unused port, wrong `DATABASE_URL`) produce the intended FAIL lines;
`tsc --noEmit` clean, `eslint` clean, `next build` succeeds.

**Follow-up (same day):** the reporter's `curl.exe http://127.0.0.1:8000/health`
returned a healthy payload, proving the API was up and the earlier refusals were
a *timing* problem (page opened while uvicorn was down/restarting). Measured the
exact behaviour: with the API stopped the Next proxy answers `500` immediately;
after starting it again the same `/health` through the proxy returns `200`
without restarting Next — only the client-side query has to run again. So the UI
now heals itself:

* `app/providers.tsx` — React Query retries `ApiError.status === 0`
  (connection refused) up to 5 times with exponential backoff (1s → 8s), keeps
  one retry for real API errors, and refetches on window focus/reconnect.
* `components/shared/error-state.tsx` — while the backend is unreachable the
  panel retries every 5s (max ~2 min) with a live “retrying automatically” note
  and a `curl.exe` hint, and clears itself when the API answers.
* `components/layout/sidebar.tsx` — health badge polls every 10s while down and
  60s while healthy, so “API unavailable” flips back on its own.

### 2026-10-31 — LinkedIn/Indeed scraping via python-jobspy + this handoff file

**Added**
* `backend/app/sources/jobspy_source.py` — `JobSpySourceAdapter`: availability
  gating (`JOBSPY_ENABLED`, `JOBSPY_SITES`, installed package), row mapping,
  date-only handling, term loop, request delay/lock, provider error + warning
  extraction, dedupe inside a batch.
* `backend/requirements-scraping.txt` — optional `python-jobspy>=1.4,<2.0`.
* `backend/tests/test_jobspy_source.py` — 37 tests with mocked `scrape_jobs`
  (mapping, precision, availability, error surfacing, refresh runs, dedupe,
  saved-search resolution, freshness semantics).
* `backend/alembic/versions/20261031_1416_868a9d33f328_add_published_at_is_date_only_to_jobs.py`.
* `session.md` (this file).

**Changed**
* `sources/linkedin.py`, `sources/indeed.py` — now real jobspy adapters with
  dynamic availability, reasons and `setup_command`.
* `sources/base.py` — `NormalizedJob.published_at_is_date_only`,
  `FetchResult.errors`, `SourceAdapter.setup_command`.
* `sources/registry.py` — adapters receive settings.
* `services/refresh.py` — `apply_saved_search()` (saved titles/keywords/location/
  posting age used when a refresh has no hints) and provider-error statuses
  (`failed` when nothing usable was fetched, `partial` otherwise).
* `services/ingestion.py` — stores the date-only flag, upgrades a date-only
  timestamp to an exact one when a later refresh knows it.
* `services/jobs.py` / `services/dashboard.py` — `published_since()` window that
  honours date-only postings.
* `models/job.py`, `schemas/job.py`, `schemas/source.py` — new column/fields.
* `core/config.py` — `JOBSPY_*` settings + site validation.
* `tests/conftest.py` — `JOBSPY_ENABLED=false` for the suite; two existing tests
  updated to the new “opt-in” contract.
* Frontend: `types/index.ts`, `lib/utils.ts` (`describePostingAge`),
  `components/jobs/job-card.tsx`, `components/jobs/job-detail-dialog.tsx`,
  `components/jobs/refresh-control.tsx`, `components/shortlist/shortlist-card.tsx`,
  `app/page.tsx` (date-only labels), `app/settings/page.tsx` (availability
  badge, “How to enable”, scraping guard-rails card, live scraping status).
* Docs: `README.md` (provider table, env table, new “Turn on LinkedIn scraping”
  section, limitations, next steps), `docs/job-sources.md` (rewritten
  LinkedIn/Indeed sections + refresh semantics), `backend/.env.example`.

**Verification** — see §7 (121 tests, ruff, tsc, lint, build, live pages, live
jobspy failure path).

### 2026-10-29/30 — Initial MVP (merged to `main` via PR #1)

* Backend: FastAPI + SQLAlchemy 2 + Alembic + psycopg3, jobs/shortlist/
  applications/dashboard/settings/sources endpoints, ingestion + dedupe,
  fixture provider + manual import, in-process scheduler, 84 tests.
* Frontend: Next.js 15 App Router, Tailwind + shadcn-style primitives, TanStack
  Query, recharts, all five pages, error/empty/loading states, 404 + error
  boundaries, same-origin API proxy.
* Infra/docs: `docker-compose.yml` (Postgres only), `.env.example`, `.gitignore`,
  README, `docs/job-sources.md`.

---

## 11. Guard-rails for the next agent

1. **Do not claim a source works unless it actually ran.** A blocked or throttled
   scrape is `failed`/`partial` with the provider message; never “no new jobs”.
2. **Never fabricate listings or timestamps** to fill a gap. Missing publication
   time stays `NULL`; date-only postings keep their flag.
3. **Applications stay manual.** Nothing may auto-create an application when a
   user opens a listing.
4. **Do not commit secrets.** `.env`, `.env.local`, credentials and tokens are
   git-ignored — only `*.env.example` files belong in the repo.
5. **No force-push, no history rewriting, no destructive branch operations.**
6. **Keep the test suite offline.** Monkeypatch `jobspy_source._run_scrape`;
   `JOBSPY_ENABLED=false` is the suite default.
7. **Update this file** (session log + verified-state table) whenever behaviour,
   tests or commands change.
