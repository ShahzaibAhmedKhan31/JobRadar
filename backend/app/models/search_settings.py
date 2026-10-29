"""Persisted search preferences (single row, single user)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base

SINGLETON_ID = 1


class SearchSettings(Base):
    __tablename__ = "search_settings"
    __table_args__ = (
        CheckConstraint(
            "default_work_arrangement IN ('any', 'remote', 'hybrid', 'onsite')",
            name="work_arrangement_valid",
        ),
        CheckConstraint(
            "default_experience_level IN ('any', 'entry', 'associate', 'mid_senior')",
            name="experience_level_valid",
        ),
        CheckConstraint(
            "default_posting_age_hours BETWEEN 1 AND 720",
            name="posting_age_range",
        ),
        CheckConstraint(
            "scheduled_refresh_interval_minutes BETWEEN 15 AND 1440",
            name="refresh_interval_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=SINGLETON_ID)
    default_titles: Mapped[str | None] = mapped_column(String(300), nullable=True)
    default_keywords: Mapped[str | None] = mapped_column(String(300), nullable=True)
    default_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    default_work_arrangement: Mapped[str] = mapped_column(
        String(32), nullable=False, default="any", server_default="any"
    )
    default_experience_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="any", server_default="any"
    )
    default_posting_age_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=168, server_default="168"
    )
    default_sources: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    scheduled_refresh_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    scheduled_refresh_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, server_default="60"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SearchSettings age={self.default_posting_age_hours}h>"
