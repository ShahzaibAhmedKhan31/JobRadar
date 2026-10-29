"""Search preferences persistence (single row)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import BadRequestError
from app.core.time import ensure_utc, utcnow
from app.models.search_settings import SINGLETON_ID, SearchSettings
from app.schemas.settings import SearchSettingsRead, SearchSettingsUpdate
from app.sources.registry import SourceRegistry


def get_settings_row(db: Session) -> SearchSettings | None:
    return db.get(SearchSettings, SINGLETON_ID)


def get_or_create_settings(
    db: Session, *, settings: Settings | None = None
) -> SearchSettings:
    settings = settings or get_settings()
    row = get_settings_row(db)
    if row is not None:
        return row
    row = SearchSettings(
        id=SINGLETON_ID,
        default_work_arrangement="any",
        default_experience_level="any",
        default_posting_age_hours=168,
        scheduled_refresh_enabled=settings.scheduled_refresh_enabled,
        scheduled_refresh_interval_minutes=settings.scheduled_refresh_interval_minutes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_read(row: SearchSettings) -> SearchSettingsRead:
    return SearchSettingsRead(
        default_titles=row.default_titles,
        default_keywords=row.default_keywords,
        default_location=row.default_location,
        default_work_arrangement=row.default_work_arrangement,  # type: ignore[arg-type]
        default_experience_level=row.default_experience_level,  # type: ignore[arg-type]
        default_posting_age_hours=row.default_posting_age_hours,
        default_sources=list(row.default_sources or []),
        scheduled_refresh_enabled=row.scheduled_refresh_enabled,
        scheduled_refresh_interval_minutes=row.scheduled_refresh_interval_minutes,
        updated_at=ensure_utc(row.updated_at),
    )


def read_settings(db: Session, *, settings: Settings | None = None) -> SearchSettingsRead:
    return to_read(get_or_create_settings(db, settings=settings))


def update_settings(
    db: Session,
    payload: SearchSettingsUpdate,
    *,
    registry: SourceRegistry,
    settings: Settings | None = None,
) -> SearchSettingsRead:
    provided = payload.model_dump(exclude_unset=True)
    if "default_sources" in provided and provided["default_sources"] is not None:
        unknown = set(provided["default_sources"]) - registry.known_keys()
        if unknown:
            raise BadRequestError(
                f"Unknown source(s) in default_sources: {', '.join(sorted(unknown))}"
            )
    row = get_or_create_settings(db, settings=settings)
    for field, value in provided.items():
        setattr(row, field, value)
    row.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return to_read(row)


def schedule_config(
    db: Session, *, settings: Settings | None = None
) -> tuple[bool, int]:
    """Return ``(enabled, interval_minutes)`` for the background scheduler."""
    settings = settings or get_settings()
    row = get_settings_row(db)
    if row is None:
        return (
            settings.scheduled_refresh_enabled,
            settings.scheduled_refresh_interval_minutes,
        )
    return row.scheduled_refresh_enabled, row.scheduled_refresh_interval_minutes
