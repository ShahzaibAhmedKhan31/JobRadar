"""JobRadar FastAPI application."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import ProgrammingError

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.db.schema_check import UPGRADE_COMMAND, ensure_schema
from app.db.session import engine
from app.db.wait import wait_for_database
from app.services.scheduler import RefreshScheduler
from app.sources.registry import build_registry

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.settings = settings
    app.state.registry = build_registry(settings)
    if settings.db_wait_on_startup and not settings.is_sqlite:
        wait_for_database(
            engine,
            attempts=settings.db_wait_attempts,
            interval_seconds=settings.db_wait_interval_seconds,
        )
    app.state.schema = ensure_schema(engine, settings)
    scheduler = RefreshScheduler(app.state.registry, settings)
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info(
        "JobRadar API ready (env=%s, sources=%s)",
        settings.environment,
        ", ".join(app.state.registry.keys()),
    )
    try:
        yield
    finally:
        await scheduler.stop()


DESCRIPTION = """
Personal job discovery and application tracking API.

**Timestamp semantics**
* `published_at` is the publication time reported by the source and is `null`
  when the source does not expose one — it is never derived from discovery time.
* `first_seen_at` records when JobRadar first imported the listing.
* Posting-age filters use `published_at` only. Jobs with an unknown publication
  time are excluded unless `include_unknown_published=true` is passed.

**Sources** — LinkedIn and Indeed listings are retrieved with the optional
`python-jobspy` extra, which reads the boards' public guest search pages. That is
opt-in scraping: set `JOBSPY_ENABLED=true` and list the site in `JOBSPY_SITES`,
and install `backend/requirements-scraping.txt`. Blocks and throttling are
reported as failed refresh runs, never as empty successes. See
`docs/job-sources.md`.

**Test data** — sample-feed rows are flagged and excluded from dashboard metrics
unless `include_test_data=true` is passed explicitly.
"""

app = FastAPI(
    title="JobRadar API",
    version=settings.app_version,
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "jobs", "description": "Discovery, refresh and manual import."},
        {"name": "shortlist", "description": "Jobs saved for later review."},
        {"name": "applications", "description": "Manual application tracking."},
        {"name": "dashboard", "description": "Aggregated metrics."},
        {"name": "settings", "description": "Search defaults and automatic refresh."},
        {"name": "sources", "description": "Provider availability."},
        {"name": "health", "description": "Liveness checks."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


#: PostgreSQL SQLSTATE codes that mean "the schema is not what the code expects".
SCHEMA_ERROR_CODES = {
    "42703": "column",  # undefined_column
    "42P01": "table",  # undefined_table
    "42704": "type",  # undefined_object
}


def schema_error_payload(exc: ProgrammingError) -> tuple[int, dict[str, str]]:
    """Map a programming error to ``(status, body)`` with a fix when it is drift."""
    code = getattr(getattr(exc, "orig", None), "sqlstate", None)
    missing = SCHEMA_ERROR_CODES.get(str(code))
    if missing is None:
        return 500, {"detail": "Database error.", "code": "database_error"}
    name = _missing_object_name(exc)
    label = f"{missing} {name}".strip()
    message = (
        f"The database is missing {label}. The schema is older than the code — run "
        f"`{UPGRADE_COMMAND}` from the backend directory and restart the API."
    )
    return 503, {"detail": message, "code": "schema_out_of_date"}


@app.exception_handler(ProgrammingError)
async def schema_error_handler(request: Request, exc: ProgrammingError) -> JSONResponse:
    """Turn a missing column/table into an actionable 503 instead of a 500."""
    status_code, content = schema_error_payload(exc)
    if status_code == 500:
        logger.exception("Unhandled database programming error on %s", request.url.path)
    else:
        logger.error("%s (%s)", content["detail"], request.url.path)
    return JSONResponse(status_code=status_code, content=content)


#: psycopg does not always fill ``Diagnostic.column_name``; the primary message
#: ("column \"x\" does not exist") is the reliable fallback.
#: Names appear quoted for a direct reference ("column \"x\" does not exist")
#: and unquoted (optionally schema-qualified) inside a WHERE clause.
_MISSING_OBJECT_PATTERN = re.compile(
    r'(?:column|relation|table|type)\s+"?(?P<name>[\w.]+)"?', re.IGNORECASE
)


def _missing_object_name(exc: ProgrammingError) -> str:
    orig = getattr(exc, "orig", None)
    diagnostic = getattr(orig, "diag", None)
    name = getattr(diagnostic, "column_name", None) or getattr(
        diagnostic, "table_name", None
    )
    if name:
        return str(name)
    message = getattr(diagnostic, "message_primary", None) or str(orig or exc)
    match = _MISSING_OBJECT_PATTERN.search(message)
    return match.group("name") if match else ""


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": "JobRadar API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_prefix)
