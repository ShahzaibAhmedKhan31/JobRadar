# JobRadar

A personal job-discovery and application-tracking workspace. JobRadar imports
recent listings into your own PostgreSQL database, lets you filter them by
posting age, location, arrangement, level and keywords, shortlist the good ones
with notes and priority, and manually record every application you submit.

Everything runs locally: PostgreSQL in Docker, the FastAPI backend and the
Next.js frontend directly on your machine.

> **Status:** personal-use MVP. No authentication, no multi-tenancy, no paid
> services. Applying stays a manual action — JobRadar never submits anything.

---

## What you can do

| Area | Capabilities |
| --- | --- |
| **Dashboard** | Live metrics from stored rows: total/discovered jobs, shortlist size, applications submitted, in progress, interviews, offers, upcoming follow-ups. Activity area chart (discovered vs. applied) and recent listings. Sample data is excluded unless you opt in. |
| **Discover jobs** | Filter by multiple titles, skills/keywords, location/remote, posting age (6/12/24/48 h or 7 days), work arrangement, experience level and source. Full-text search, sorting (newest / best match / oldest / company), pagination. Cards show title, company, location, arrangement, source, publication time + posting age, discovery time, summary, tracking status and duplicate hints. Open the original listing in a new tab, shortlist, or start tracking. |
| **Shortlist** | Save/remove jobs, set High/Medium/Low priority, keep private notes, filter by source, priority and date, open the listing, and move a job into the application tracker. Notes and priority survive source refreshes and shortlisting never marks a job as applied. |
| **Applications** | Seven statuses (Saved, Applied, Assessment, Interview, Offer, Rejected, Withdrawn), application date, follow-up date, resume reference and notes. Table and Kanban board views, search and filters by status/company/date, duplicate prevention, edit/delete. |
| **Refresh & history** | Manual refresh per source or all sources, with new/updated/unchanged counts and error reporting stored per run. Optional in-process scheduled refresh controlled from Search Settings. |
| **Search Settings** | Default filters, source availability with reasons, automatic-refresh interval, refresh history. |
| **Manual import** | Paste a LinkedIn/Indeed/other listing you found yourself (title, company, URL, optional metadata). This is the authorized path for platforms without an official search API. |

---

## Architecture

```
┌──────────────────────────┐        HTTP (relative /api)        ┌───────────────────────────┐
│  Next.js 15 (App Router) │ ─────────────────────────────────▶ │  Next.js server rewrites  │
│  React 19 + Tailwind     │                                    │  /api/*  → FastAPI :8000  │
└──────────────────────────┘                                    └─────────────┬─────────────┘
                                                                              │
                                                                ┌─────────────▼─────────────┐
                                                                │ FastAPI (Python 3.11+)    │
                                                                │ SQLAlchemy 2 + Pydantic   │
                                                                │ service layer + adapters  │
                                                                └─────────────┬─────────────┘
                                                                              │ psycopg 3
                                                                ┌─────────────▼─────────────┐
                                                                │ PostgreSQL 16 (Docker)    │
                                                                │ named volume, healthcheck │
                                                                └───────────────────────────┘
```

The browser only talks to the Next.js origin. A server-side rewrite proxies
`/api/*` and `/health` to FastAPI, so there is no browser CORS to manage and the
app also works behind a preview proxy.

### Source adapters

Every provider implements `SourceAdapter` (`backend/app/sources/base.py`) and
returns provider-neutral `NormalizedJob` objects. The API, database and UI know
nothing about specific job boards, so new providers only require a new adapter
plus a registry entry. See **[docs/job-sources.md](docs/job-sources.md)**.

| Provider | Status | Notes |
| --- | --- | --- |
| `linkedin` | **Available via opt-in scraping** | Guest search read through [`python-jobspy`](https://pypi.org/project/python-jobspy/); needs `requirements-scraping.txt`. May breach LinkedIn's User Agreement and can be throttled. |
| `indeed` | **Opt-in required** | Same adapter; add `indeed` to `JOBSPY_SITES` (Indeed's Publisher API was retired in 2020). |
| `manual_import` | Available (no retrieval) | User-pasted listings, optionally attributed to LinkedIn/Indeed. |
| `fixtures` | Available | 26 clearly-labelled synthetic listings for demos and tests; flagged `is_test_data`. |

A source that cannot run is never reported as a successful import: the refresh
records a `skipped` run with the reason, and the UI shows the exact command or
environment variable needed to enable it.

---

## Repository layout

```
JobRadar/
├── backend/
│   ├── app/
│   │   ├── api/            # deps.py, router.py, routes/{jobs,shortlist,applications,dashboard,settings,sources,health}
│   │   ├── core/           # config, enums, errors, logging, time, text/url helpers
│   │   ├── db/             # declarative base, engine/session, startup wait, enum type
│   │   ├── models/         # jobs, shortlisted_jobs, applications, job_fetch_runs, search_settings
│   │   ├── schemas/        # Pydantic request/response contracts + serializers
│   │   ├── services/       # ingestion, refresh, jobs, shortlist, applications, dashboard, scheduler, imports
│   │   ├── sources/        # base adapter, registry, fixtures/linkedin/indeed/manual_import
│   │   └── main.py         # FastAPI app, lifespan, CORS, error mapping
│   ├── alembic/            # env.py + initial migration
│   ├── tests/              # 121 pytest tests (PostgreSQL by default, SQLite fallback)
│   ├── alembic.ini
│   ├── pyproject.toml      # pytest + ruff configuration
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── app/                # layout, dashboard, discover, shortlist, applications, settings
│   ├── components/
│   │   ├── ui/             # shadcn-style primitives (button, card, dialog, select, table, …)
│   │   ├── layout/         # sidebar + app shell
│   │   ├── jobs/           # job card, filters, detail/track/import dialogs, refresh control
│   │   ├── shortlist/      # shortlist card editor
│   │   ├── applications/   # table row, board, edit dialog, track-job picker
│   │   ├── dashboard/      # activity chart, status breakdown
│   │   └── shared/         # page header, empty/error states, badges, pagination, skeletons
│   ├── lib/                # api client, TanStack Query hooks, formatters, constants
│   ├── types/              # TypeScript mirrors of the API schemas
│   ├── package.json
│   └── .env.example
├── docs/job-sources.md
├── docker-compose.yml      # PostgreSQL 16 only
├── .env.example            # Docker Compose variables
└── README.md
```

---

## Tech stack

* **Frontend:** Next.js 15 (App Router), TypeScript, React 19, Tailwind CSS 3,
  shadcn/ui-style components on Radix primitives, TanStack Query, Recharts,
  Sonner toasts, lucide icons.
* **Backend:** Python 3.11+ (3.12 works), FastAPI, Pydantic v2, SQLAlchemy 2,
  Alembic, psycopg 3.
* **Database:** PostgreSQL 16 in Docker with a persistent named volume.
* **Tests:** pytest (backend), ruff, TypeScript, ESLint, `next build`.

---

## Prerequisites

| Tool | Version | Windows check |
| --- | --- | --- |
| Git | any recent | `git --version` |
| Docker Desktop | with Compose v2 | `docker compose version` |
| Python | 3.11 or 3.12 | `python --version` |
| Node.js | 20 LTS or newer | `node --version` |
| npm | bundled with Node | `npm --version` |

> Windows: install Python from python.org (tick “Add python.exe to PATH”), Node
> from nodejs.org, and Docker Desktop with WSL 2 enabled.

---

## Quick start (Windows PowerShell)

### 1. Get the code

```powershell
git clone https://github.com/ShahzaibAhmedKhan31/JobRadar.git
cd JobRadar
git switch main
git pull
```

The MVP lives on the `arena/1306ca20-jobradar` branch; fetch it with
`git fetch origin arena/1306ca20-jobradar` and
`git switch arena/1306ca20-jobradar` if you are reviewing the feature branch
before it is merged.

### 2. Create environment files

```powershell
Copy-Item .env.example .env                 # Docker Compose (Postgres credentials)
Copy-Item backend\.env.example backend\.env   # FastAPI (DATABASE_URL, CORS, scheduler)
Copy-Item frontend\.env.example frontend\.env.local  # Next.js API proxy target
```

These files are git-ignored. Defaults already match the Compose container, so no
edits are required for a standard local setup.

### 3. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d postgres
docker compose ps
```

Wait until the `jobradar-postgres` container reports **healthy**. Data lives in
the `jobradar_postgres_data` volume and survives restarts.

### 4. Set up and run the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
# optional: enables LinkedIn/Indeed scraping (see the scraping section below)
pip install -r requirements-scraping.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and retry.

* API: <http://localhost:8000>
* Swagger UI: <http://localhost:8000/docs>

Leave this terminal running. If anything looks wrong later, run
`.\.venv\Scripts\python.exe scripts\preflight.py` from the repository root —
it names the failing piece and the command that fixes it.

### 5. Set up and run the frontend

Open a **second** terminal:

```powershell
cd JobRadar\frontend
npm install
npm run dev
```

* App: <http://localhost:3000>

The Next.js server proxies `/api/*` to `http://127.0.0.1:8000` (configurable via
`API_PROXY_TARGET` in `frontend\.env.local`).

### 6. First run

1. Open <http://localhost:3000>.
2. Click **Refresh sources** — the bundled sample feed imports 26 synthetic
   listings. They are marked **sample** and hidden from dashboard metrics.
3. Explore **Discover Jobs**, shortlist a couple of roles, add notes and
   priorities, then **Track application** on one of them.
4. On the dashboard, toggle **Include sample data** to see those rows in the
   metrics, or import a real listing with **Import job link** to start your own
   clean dataset.

### 7. (Optional) Turn on LinkedIn scraping

The LinkedIn adapter is real but **opt-in**, because it reads LinkedIn's public
guest search pages through `python-jobspy` — scraping, not an authorized API.
That may breach LinkedIn's User Agreement and can be throttled or blocked. Only
enable it if that trade-off is acceptable to you.

```powershell
# in the backend venv (from the repository root)
pip install -r backend/requirements-scraping.txt

# backend/.env — opt in explicitly
JOBSPY_ENABLED=true
JOBSPY_SITES=linkedin
JOBSPY_RESULTS_WANTED=25
JOBSPY_MAX_SEARCH_TERMS=3
JOBSPY_REQUEST_DELAY_SECONDS=2
```

Restart the API, then either fill in **Search Settings** (titles, keywords, city)
or type the filters directly on **Discover jobs** — the refresh button on that
page sends exactly what is on screen. Press **Refresh sources**. What to expect:

* A healthy run stores new listings and shows `success` in refresh history; the
  LinkedIn card becomes **Available** and Discover lists the rows with a
  LinkedIn badge.
* A throttled or blocked scrape shows the provider message (for example
  `429 Too Many Requests` or `unexpected page with no jobs (blocked?)`) and the
  run is `failed` — JobRadar does not retry with a new identity, solve a
  CAPTCHA, or invent listings.
* LinkedIn only exposes the posting **date**, so those cards read
  “date only” and the freshness filter treats the whole day as within the
  window.
* Want Indeed too? Add it: `JOBSPY_SITES=linkedin,indeed`.
* Want scraping gone entirely? Set `JOBSPY_ENABLED=false` (or do not install the
  extra). Manual import keeps working.
* **Discovery does not scrape.** `GET /api/jobs` only searches rows already
  stored in PostgreSQL; scraping happens on `POST /api/jobs/refresh`. The
  response echoes `applied_query` (terms, location, window, limit) and, when
  nothing new arrives, the message states what was searched — so an empty list
  can be told apart from an empty scrape. If the terms are missing, the run
  warns that the board was queried without keywords.
* Each configured title is one HTTP request (capped by
  `JOBSPY_MAX_SEARCH_TERMS`, default 3), so three roles ≈ three requests with a
  2 s gap; the response lists the terms that actually ran.

> Verify the live path on your machine after installing: the build environment
> used to develop this feature could not reach linkedin.com, so the adapter is
> covered by tests with mocked jobspy responses, not by a live scrape.

---

## Everyday workflow

1. **Refresh** a source (or enable automatic refresh in Search Settings). With
   `python-jobspy` installed this searches your saved titles on LinkedIn; without
   it only the sample feed and manual import are available.
2. **Discover**: set titles/keywords/location/posting age, apply, then sort by
   best match.
3. **Shortlist** promising roles; store notes and a priority.
4. Apply on the company site yourself.
5. **Track application**: pick the job, set status *Applied* and today's date,
   add a resume reference and follow-up date.
6. Move the status forward (Assessment → Interview → Offer / Rejected /
   Withdrawn) as you hear back.
7. Check the **Dashboard** for pipeline health and upcoming follow-ups.

Opening a job listing never creates an application. Only the tracking dialog
does.

---

## macOS / Linux commands

```bash
# PostgreSQL
docker compose up -d postgres

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Environment variables

### Root `.env` (Docker Compose)

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_DB` | `jobradar` | Database name |
| `POSTGRES_USER` | `jobradar` | Database role |
| `POSTGRES_PASSWORD` | `jobradar` | Database password (local only) |
| `POSTGRES_PORT` | `5432` | Host port mapped to the container |

### `backend/.env`

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://jobradar:jobradar@localhost:5432/jobradar` | SQLAlchemy URL (use `127.0.0.1` if `localhost` resolves to IPv6) |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated browser origins allowed to call the API directly |
| `ENVIRONMENT` | `development` | Shown in `/health` |
| `LOG_LEVEL` | `INFO` | Root log level |
| `DB_WAIT_ON_STARTUP` | `true` | Retry connecting while Postgres boots |
| `SCHEMA_CHECK_ON_STARTUP` | `true` | Compare the database's Alembic revision with the code and refuse to start when they differ |
| `SCHEMA_AUTO_UPGRADE` | `false` | Apply pending migrations automatically at startup instead of refusing |
| `MAX_REFRESH_JOBS_PER_SOURCE` | `500` | Upper bound per manual refresh |
| `ENABLED_SOURCES` | *(empty = all)* | Optional allow-list, e.g. `fixtures,manual_import` |
| `SCHEDULER_ENABLED` | `true` | Master switch for the in-process scheduler |
| `SCHEDULED_REFRESH_ENABLED` | `false` | Seeds the automatic-refresh toggle in Search Settings |
| `SCHEDULED_REFRESH_INTERVAL_MINUTES` | `60` | Seeds the default interval (15–1440) |
| `SCHEDULER_TICK_SECONDS` | `30` | How often the scheduler checks whether a run is due |
| `JOBSPY_ENABLED` | `true` | Hard switch for the optional scraping adapter; `false` keeps JobRadar offline |
| `JOBSPY_SITES` | `linkedin` | Comma-separated boards to scrape (`indeed`, `glassdoor`, … to opt in) |
| `JOBSPY_RESULTS_WANTED` | `25` | Listings requested per search term |
| `JOBSPY_MAX_SEARCH_TERMS` | `3` | Saved titles/keywords turned into requests (one request each); the response reports the terms that actually ran |
| `JOBSPY_REQUEST_DELAY_SECONDS` | `2` | Delay between scrape requests (politeness) |
| `JOBSPY_PROXIES` | *(empty)* | Optional rotating proxies for jobspy |
| `JOBSPY_COUNTRY` | `pakistan` | Country hint for the Indeed scraper only |
| `JOBSPY_FETCH_DESCRIPTION` | `false` | Fetch full descriptions (extra request per listing) |
| `JOBSPY_VERBOSE` | `0` | jobspy log level: 0 quiet, 1 normal, 2 debug |

### `frontend/.env.local`

| Variable | Default | Purpose |
| --- | --- | --- |
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Where Next.js proxies `/api/*` and `/health` |
| `NEXT_PUBLIC_API_BASE_URL` | *(empty = same origin)* | Only set this if the browser should call FastAPI directly |

Secrets stay in local `.env` files. Nothing sensitive is compiled into the
frontend bundle, and no provider credentials are required for the MVP.

---

## Database and migrations

> **Pulling new code? Run the migrations.** Every commit that changes the schema
> ships an Alembic revision; the API refuses to start when the database is older
> than the code, printing exactly what to run:
>
> ```
> RuntimeError: Database schema does not match the code. database schema is behind
> the code: database at c54269e5d2c5, code expects 868a9d33f328.
> Run `alembic upgrade head` from backend/.
> ```
>
> ```powershell
> cd backend; .\.venv\Scripts\Activate.ps1; alembic upgrade head
> ```
>
> If you would rather have the API migrate itself, set `SCHEMA_AUTO_UPGRADE=true`.
> Either way, migrations are the only supported way to change the schema.

The schema is created by Alembic:

```powershell
cd backend
alembic upgrade head        # apply migrations
alembic current             # show the applied revision
alembic check               # verify models match the database (no drift)
```

Tables:

| Table | Purpose |
| --- | --- |
| `jobs` | Normalized listings; UUID PK, `(source, source_job_id)` partial unique index plus a URL/title/company fingerprint fallback; `published_at` nullable and distinct from `first_seen_at`; `is_test_data` flag. |
| `shortlisted_jobs` | One row per job, priority enum, notes, timestamps. |
| `applications` | One row per job (unique), status enum, nullable application/follow-up dates, notes, resume reference, DB check that follow-up ≥ application date. |
| `job_fetch_runs` | One row per source per refresh: trigger, status, timestamps, fetched/new/updated/unchanged counts, error message. |
| `search_settings` | Single row with default filters and automatic-refresh preferences. |

All timestamps are timezone-aware and stored in UTC. Enums are stored as
`VARCHAR` with check constraints for portable migrations.

Creating a new migration after a model change:

```powershell
alembic revision --autogenerate -m "describe the change"
# review the generated file, then
alembic upgrade head
```

---

## API overview

Interactive documentation: <http://localhost:8000/docs> (OpenAPI JSON at
`/openapi.json`). All application endpoints are prefixed with `/api`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness + database check |
| `GET` | `/api/jobs` | Filter/sort/paginate stored jobs (`q`, `titles`, `keywords`, `location`, `max_age_hours`, `include_unknown_published`, `work_arrangement`, `experience_level`, `sources`, `shortlisted`, `application_status`, `include_test_data`, `sort`, `page`, `page_size`) |
| `GET` | `/api/jobs/{job_id}` | Job detail incl. description and possible duplicates |
| `POST` | `/api/jobs/refresh` | Refresh one/all sources; returns per-source runs, counts and messages |
| `GET` | `/api/jobs/refresh-history` | Paginated refresh runs |
| `POST` | `/api/jobs/import` | Record a manual listing (returns `201` when created, `200` when it already existed) |
| `GET` | `/api/shortlist` | Shortlisted jobs (filters: sources, priority, date range, search, sort) |
| `POST` | `/api/shortlist/{job_id}` | Shortlist a job (idempotent upsert) |
| `PATCH` | `/api/shortlist/{job_id}` | Update priority/notes |
| `DELETE` | `/api/shortlist/{job_id}` | Remove from shortlist |
| `GET` | `/api/applications` | Paginated applications (status[], company, search, date range, sort) |
| `POST` | `/api/applications` | Create a tracking record (409 if the job already has one) |
| `GET` | `/api/applications/{id}` | Application detail |
| `PATCH` | `/api/applications/{id}` | Update status/dates/notes/resume |
| `DELETE` | `/api/applications/{id}` | Delete a tracking record |
| `GET` | `/api/dashboard/summary` | Metrics for a recent period (test data excluded by default) |
| `GET` | `/api/dashboard/activity` | Daily discovered/applied series (1–90 days) |
| `GET` | `/api/settings` | Search defaults + scheduler preferences |
| `PUT` | `/api/settings` | Update search defaults / automatic refresh |
| `GET` | `/api/sources` | Provider availability, stored counts, last run |

Validation failures return `422`, missing rows `404`, conflicts `409`, provider
refusals `400`/`409`, and upstream provider errors are captured per run rather
than crashing the request. Pagination is capped at 100 items per page.

### Timestamp semantics

* `published_at` — publication time **reported by the source**, or `null` when
  unknown. It is never derived from discovery time.
* `first_seen_at` — when JobRadar first imported the row.
* `last_seen_at` — when a refresh last saw the row.
* Posting-age filters use `published_at` only. Jobs with an unknown publication
  time are excluded and reported through `unknown_published_count`; opt in with
  `include_unknown_published=true`.

---

## Tests and quality checks

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:TEST_DATABASE_URL = "postgresql+psycopg://jobradar:jobradar@localhost:5432/jobradar_test"
pytest                    # 121 tests
ruff check app tests
```

* The suite uses a **dedicated test database** (`jobradar_test`) and refuses to
  run unless its name ends with `_test`. Every test runs in a transaction that
  is rolled back, so your development data is never touched.
* Create the test database once:
  `docker exec -it jobradar-postgres createdb -U jobradar jobradar_test`
  (or `docker compose exec postgres createdb -U jobradar jobradar_test`).
* If PostgreSQL is unreachable, the suite falls back to a temporary SQLite file
  so tests still run; PostgreSQL remains the primary target.
* Coverage for the key behaviour: ingestion/normalization, URL validation,
  fingerprint dedupe, posting-age filtering, missing publication timestamps,
  provider failures and partial batches, shortlist CRUD + refresh persistence,
  application lifecycle/conflicts, dashboard metrics/activity, settings,
  sources, health, and Alembic upgrade/downgrade.

### Frontend

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```

### Optional coverage

```powershell
cd backend
pytest --cov=app --cov-report=term-missing
```

---

## Stopping and cleaning up

```powershell
# Stop PostgreSQL but keep all data
docker compose stop postgres

# Remove the container and network, keep the named volume (data preserved)
docker compose down

# DANGER: also delete the database volume
docker compose down -v
```

Stop the API and frontend with `Ctrl+C` in their terminals.

---

## Troubleshooting

### First stop: run the preflight doctor

When the UI shows errors (for example `connect ECONNREFUSED 127.0.0.1:8000`),
run this from the repository root with the **backend virtualenv** Python. It
checks Python, dependencies, `.env` files, the database, migrations, ports,
frontend dependencies and the scraping extra, and prints the exact fix:

```powershell
# Windows (repo root)
.\.venv\Scripts\python.exe scripts\preflight.py
# macOS / Linux
./.venv/bin/python scripts/preflight.py
```

Typical output when the API was never started:

```
[FAIL] FastAPI on port 8000   nothing is listening — the frontend proxy cannot reach it
       -> Start it in a second terminal: cd backend; uvicorn app.main:app --reload --port 8000
```

### `connect ECONNREFUSED 127.0.0.1:8000` in the Next.js log

The frontend is fine; FastAPI is not listening. In order of likelihood:

1. **The backend terminal exited.** Scroll up in that window — the cause is
   there. If PostgreSQL was not up, uvicorn fails during the startup DB wait.
   Start it with `docker compose up -d postgres` (Docker Desktop must be running)
   and check `docker compose ps` reports `healthy`.
2. **Wrong folder.** `uvicorn app.main:app` only works from `backend/`; from the
   repository root it exits with `ModuleNotFoundError: No module named 'app'`.
3. **Port already taken.** uvicorn prints `[Errno 10048] error while attempting
   to bind on address ('127.0.0.1', 8000)`. Find it with
   `netstat -ano | findstr :8000`, then either stop that process or run
   `uvicorn app.main:app --port 8001` and set `API_PROXY_TARGET=http://127.0.0.1:8001`
   in `frontend/.env.local` (restart `npm run dev` afterwards).
4. **Virtualenv not active.** The prompt should start with `(.venv)`; otherwise
   `uvicorn` is not on PATH at all.
5. **Backend and frontend in the same terminal.** `Ctrl+C` on the frontend also
   stopped the API. Use two terminals.
6. **Only one of them is bound to IPv6.** Keep the API on `127.0.0.1` and the
   proxy target on `http://127.0.0.1:8000` (both IPv4).

A quick check that the API itself is healthy, independent of the frontend:

```powershell
curl.exe http://127.0.0.1:8000/health
# {"status":"ok","database":"ok","version":"0.1.0",...}
```

| Symptom | Fix |
| --- | --- |
| `docker compose` not recognised | Update Docker Desktop (Compose v2) and restart the terminal. |
| Backend exits with “Could not connect to PostgreSQL” | `docker compose ps` should show *healthy*; check `POSTGRES_PORT` vs `DATABASE_URL`. |
| `connection refused` on `::1` | Use `127.0.0.1` instead of `localhost` in `backend/.env`. |
| Port 5432 already in use | Set `POSTGRES_PORT=5433` in the root `.env` and update `DATABASE_URL`. |
| Port 3000 or 8000 in use | Stop the other process or run Next with `npm run dev -- -p 3001` and FastAPI with `--port 8001` (update `API_PROXY_TARGET`). |
| `alembic: command not found` | Activate the virtualenv first (`.\.venv\Scripts\Activate.ps1`). |
| `ECONNREFUSED 127.0.0.1:8000` in the Next.js log | FastAPI is not listening — see the section above, then run `scripts/preflight.py`. |
| `ModuleNotFoundError: No module named 'app'` | You ran `uvicorn` outside `backend/`. `cd backend` first. |
| `[Errno 10048]` / “address already in use” | Port 8000 is taken: `netstat -ano | findstr :8000`, stop that process, or move the API and set `API_PROXY_TARGET`. |
| `'uvicorn' is not recognized` | The backend virtualenv is not active (prompt should show `(.venv)`). |
| Backend exits during “Waiting for database” | PostgreSQL is down or the URL is wrong — `docker compose ps`, then `scripts/preflight.py`. |
| `column ... does not exist` / `UndefinedColumn` | The database is older than the code: `cd backend; alembic upgrade head`, then restart uvicorn. The API now refuses to start in this state instead of 500-ing per request. |
| `RuntimeError: Database schema does not match the code` on startup | Same fix — pending migration. `SCHEMA_AUTO_UPGRADE=true` opts into automatic migration instead. |
| HTTP 503 `schema_out_of_date` | Same cause, seen from the frontend when the startup check is disabled: run `alembic upgrade head`. |
| PowerShell blocks venv activation | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. |
| Dashboard shows zeros although sample data exists | Sample rows are excluded by default — use the “Include sample data” toggle. |
| Tests skip PostgreSQL | Set `TEST_DATABASE_URL` and create the `jobradar_test` database. |

---

## Limitations (MVP)

* LinkedIn and Indeed only work through `python-jobspy`, which scrapes the
  public guest pages. That is opt-in, may breach the platforms' terms, and can
  break whenever a board changes its markup or decides to block you — see
  [docs/job-sources.md](docs/job-sources.md). Manual import always works.
* LinkedIn reports only the posting **date**; those jobs carry
  `published_at_is_date_only = true` and the UI says “date only”.
* No live scraping is exercised by the test suite (it is mocked) and it was not
  validated against LinkedIn from the build sandbox, whose egress is restricted.
  Run one refresh locally to confirm the live path.
* Single user, no authentication or user table.
* Publication timestamps are only as good as the source; manual imports leave
  them empty unless you provide a date.
* The scheduled refresh runs inside the API process and only while it is running.
* Duplicate detection is a heuristic (same normalized company + title); records
  are never merged automatically.
* No drag-and-drop Kanban; status changes happen via the card/row editor.
* Resume files are referenced by name, not uploaded.

## Sensible next steps

1. **Authorized provider**: integrate a licensed job feed (Adzuna, JSearch,
   Greenhouse/Lever company boards) behind the existing `SourceAdapter` so
   retrieval does not depend on scraping.
2. **Saved searches**: persist named filter sets with per-search refresh and
   “new since last visit” counts.
3. **Email/alert ingestion**: parse job-alert emails into `POST /api/jobs/import`
   to cover LinkedIn/Indeed without scraping.
4. **Reminders**: surface follow-ups due today on the dashboard and via local
   notifications.
5. **Analytics**: response-rate and time-to-first-response per source and resume
   version.
6. **Auth & deployment**: add single-user login (or deploy behind a private
   network) before hosting it anywhere beyond localhost.
