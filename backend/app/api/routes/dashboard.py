"""Dashboard endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.dashboard import ActivityResponse, DashboardSummary
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary, summary="Dashboard metrics")
def get_summary(
    db: DbSession,
    recent_period_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    include_test_data: Annotated[bool, Query()] = False,
) -> DashboardSummary:
    return dashboard_service.get_summary(
        db,
        recent_period_hours=recent_period_hours,
        include_test_data=include_test_data,
    )


@router.get(
    "/activity", response_model=ActivityResponse, summary="Discovery/application activity"
)
def get_activity(
    db: DbSession,
    days: Annotated[int, Query(ge=1, le=90)] = 14,
    include_test_data: Annotated[bool, Query()] = False,
) -> ActivityResponse:
    return dashboard_service.get_activity(
        db, days=days, include_test_data=include_test_data
    )
