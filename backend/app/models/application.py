"""Application tracking model."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ApplicationStatus
from app.core.time import utcnow
from app.db.base import Base
from app.db.types import enum_type

if TYPE_CHECKING:
    from app.models.job import Job


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "follow_up_date IS NULL OR application_date IS NULL "
            "OR follow_up_date >= application_date",
            name="follow_up_not_before_application",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    #: One tracking record per job unless there is an explicit reason otherwise.
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        enum_type(ApplicationStatus, "application_status"),
        nullable=False,
        default=ApplicationStatus.SAVED,
        server_default=ApplicationStatus.SAVED.value,
    )
    #: Nullable until the user actually submits the application.
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resume_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    job: Mapped[Job] = relationship(back_populates="application", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Application job_id={self.job_id} status={self.status.value}>"
