"""Job source refresh history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FetchRunStatus, RefreshTrigger
from app.core.time import utcnow
from app.db.base import Base
from app.db.types import enum_type


class JobFetchRun(Base):
    __tablename__ = "job_fetch_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    trigger: Mapped[RefreshTrigger] = mapped_column(
        enum_type(RefreshTrigger, "refresh_trigger"),
        nullable=False,
        default=RefreshTrigger.MANUAL,
        server_default=RefreshTrigger.MANUAL.value,
    )
    status: Mapped[FetchRunStatus] = mapped_column(
        enum_type(FetchRunStatus, "fetch_run_status"),
        nullable=False,
        default=FetchRunStatus.RUNNING,
        server_default=FetchRunStatus.RUNNING.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_jobs_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    new_jobs_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_jobs_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    unchanged_jobs_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<JobFetchRun source={self.source} status={self.status.value}>"
