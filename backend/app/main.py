"""JobRadar FastAPI application."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
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

**Sources** — LinkedIn and Indeed connectors are intentionally disabled: neither
platform offers an authorized public job-search API. Use the bundled sample feed
and the manual import endpoint instead. See `docs/job-sources.md`.

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
