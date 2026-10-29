"""Search preferences endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import AppSettings, DbSession, RegistryDep
from app.schemas.settings import SearchSettingsRead, SearchSettingsUpdate
from app.services import search_settings as settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SearchSettingsRead, summary="Read search preferences")
def read_settings(
    db: DbSession, settings: AppSettings
) -> SearchSettingsRead:
    return settings_service.read_settings(db, settings=settings)


@router.put("", response_model=SearchSettingsRead, summary="Update search preferences")
def update_settings(
    payload: SearchSettingsUpdate,
    db: DbSession,
    registry: RegistryDep,
    settings: AppSettings,
) -> SearchSettingsRead:
    return settings_service.update_settings(
        db, payload, registry=registry, settings=settings
    )
