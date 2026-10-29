"""Aggregate API router (mounted under ``/api``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    applications,
    dashboard,
    jobs,
    search_settings,
    shortlist,
    sources,
)

api_router = APIRouter()
api_router.include_router(jobs.router)
api_router.include_router(shortlist.router)
api_router.include_router(applications.router)
api_router.include_router(dashboard.router)
api_router.include_router(search_settings.router)
api_router.include_router(sources.router)
