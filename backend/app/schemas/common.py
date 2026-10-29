"""Shared schema helpers."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls, items: list[T], *, total: int, page: int, page_size: int, **extra: object
    ) -> Page[T]:
        pages = max(1, math.ceil(total / page_size)) if total else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            **extra,
        )


def ensure_aware(value: datetime | None) -> datetime | None:
    """Normalize incoming timestamps to UTC (naive input is treated as UTC)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
