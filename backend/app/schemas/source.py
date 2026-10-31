"""Source metadata schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.constants import SourceAvailability
from app.schemas.refresh import FetchRunRead


class SourceRead(BaseModel):
    key: str
    name: str
    description: str
    availability: SourceAvailability
    availability_reason: str | None = None
    supports_refresh: bool
    can_refresh: bool
    is_test_data: bool
    docs_url: str | None = None
    required_config: list[str]
    setup_command: str | None = None
    stored_jobs_count: int = 0
    last_run: FetchRunRead | None = None


class SourcesResponse(BaseModel):
    sources: list[SourceRead]
