"""Reusable column type helpers."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=Enum)


def enum_type(enum_cls: type[E], name: str) -> SAEnum:
    """Portable enum column.

    Stored as ``VARCHAR`` plus a ``CHECK`` constraint instead of a PostgreSQL
    native enum so migrations stay simple and SQLite-based test runs behave the
    same way. Values (not member names) are persisted.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )
