"""Configured job sources."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession, RegistryDep
from app.schemas.source import SourcesResponse
from app.services.sources import list_sources

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=SourcesResponse, summary="List job sources and status")
def get_sources(db: DbSession, registry: RegistryDep) -> SourcesResponse:
    return list_sources(db, registry)
