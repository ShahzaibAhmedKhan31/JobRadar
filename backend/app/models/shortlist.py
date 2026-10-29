"""Shortlisted job model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Priority
from app.core.time import utcnow
from app.db.base import Base
from app.db.types import enum_type

if TYPE_CHECKING:
    from app.models.job import Job


class ShortlistedJob(Base):
    __tablename__ = "shortlisted_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    #: Single-user MVP: one shortlist entry per job.
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        enum_type(Priority, "shortlist_priority"),
        nullable=False,
        default=Priority.MEDIUM,
        server_default=Priority.MEDIUM.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )

    job: Mapped[Job] = relationship(back_populates="shortlist_entry", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ShortlistedJob job_id={self.job_id} priority={self.priority.value}>"
