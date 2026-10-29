"""Search settings schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WorkArrangementDefault = Literal["any", "remote", "hybrid", "onsite"]
ExperienceLevelDefault = Literal["any", "entry", "associate", "mid_senior"]
PostingAgeHours = Literal[6, 12, 24, 48, 168]


class SearchSettingsRead(BaseModel):
    default_titles: str | None = None
    default_keywords: str | None = None
    default_location: str | None = None
    default_work_arrangement: WorkArrangementDefault = "any"
    default_experience_level: ExperienceLevelDefault = "any"
    default_posting_age_hours: int = 168
    default_sources: list[str] = Field(default_factory=list)
    scheduled_refresh_enabled: bool = False
    scheduled_refresh_interval_minutes: int = 60
    updated_at: datetime | None = None


class SearchSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_titles: str | None = Field(default=None, max_length=300)
    default_keywords: str | None = Field(default=None, max_length=300)
    default_location: str | None = Field(default=None, max_length=200)
    default_work_arrangement: WorkArrangementDefault | None = None
    default_experience_level: ExperienceLevelDefault | None = None
    default_posting_age_hours: int | None = Field(default=None, ge=1, le=720)
    default_sources: list[str] | None = Field(default=None, max_length=20)
    scheduled_refresh_enabled: bool | None = None
    scheduled_refresh_interval_minutes: int | None = Field(default=None, ge=15, le=1440)
