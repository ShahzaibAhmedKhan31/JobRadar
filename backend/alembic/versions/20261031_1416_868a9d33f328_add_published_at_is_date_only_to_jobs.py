"""add published_at_is_date_only to jobs

Providers such as LinkedIn only expose the posting *date* ("posted 2 days
ago"), not the exact moment. When that happens ``published_at`` stores midnight
UTC of that day and this flag records the reduced precision so freshness
filters and the UI can treat the whole day as the window instead of pretending
we know the hour.

Revision ID: 868a9d33f328
Revises: c54269e5d2c5
Create Date: 2026-10-31 14:16:21.118365
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "868a9d33f328"
down_revision: str | None = "c54269e5d2c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "published_at_is_date_only",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "published_at_is_date_only")
