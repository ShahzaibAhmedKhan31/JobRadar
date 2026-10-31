"""Job listing model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    Uuid,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ExperienceLevel, WorkArrangement
from app.core.time import utcnow
from app.db.base import Base
from app.db.types import enum_type

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.shortlist import ShortlistedJob


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        # A source identifier is the canonical dedupe key when present.
        Index(
            "uq_jobs_source_source_job_id",
            "source",
            "source_job_id",
            unique=True,
            postgresql_where=text("source_job_id IS NOT NULL"),
            sqlite_where=text("source_job_id IS NOT NULL"),
        ),
        # Fallback fingerprint (normalized URL + title + company) when the
        # provider exposes no identifier.
        Index(
            "uq_jobs_source_external_key",
            "source",
            "external_key",
            unique=True,
            postgresql_where=text("external_key IS NOT NULL"),
            sqlite_where=text("external_key IS NOT NULL"),
        ),
        Index("ix_jobs_source_published_at", "source", "published_at"),
        Index("ix_jobs_published_at", "published_at"),
        Index("ix_jobs_first_seen_at", "first_seen_at"),
        Index("ix_jobs_company_name", "company_name"),
        CheckConstraint("length(title) > 0", name="title_not_empty"),
        CheckConstraint("length(company_name) > 0", name="company_not_empty"),
        CheckConstraint("length(job_url) > 0", name="job_url_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(250), nullable=True)
    work_arrangement: Mapped[WorkArrangement] = mapped_column(
        enum_type(WorkArrangement, "work_arrangement"),
        nullable=False,
        default=WorkArrangement.UNKNOWN,
        server_default=WorkArrangement.UNKNOWN.value,
    )
    experience_level: Mapped[ExperienceLevel] = mapped_column(
        enum_type(ExperienceLevel, "experience_level"),
        nullable=False,
        default=ExperienceLevel.UNKNOWN,
        server_default=ExperienceLevel.UNKNOWN.value,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_url: Mapped[str] = mapped_column(String(2000), nullable=False)

    #: Publication time reported by the source. NULL means "unknown" and is
    #: never fabricated from ``first_seen_at``.
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: True when the provider only reported a calendar date, so ``published_at``
    #: is midnight UTC of the posting day (LinkedIn behaves this way).
    published_at_is_date_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    is_test_data: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
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

    shortlist_entry: Mapped[ShortlistedJob | None] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    application: Mapped[Application | None] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    @property
    def has_published_at(self) -> bool:
        return self.published_at is not None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Job {self.title!r} @ {self.company_name!r} ({self.source})>"
