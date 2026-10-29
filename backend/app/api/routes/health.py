"""Service health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import AppSettings, DbSession
from app.core.errors import ServiceUnavailableError
from app.core.time import utcnow

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness and database connectivity")
def health(db: DbSession, settings: AppSettings) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        error = ServiceUnavailableError(f"Database unavailable: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "database": "unavailable",
                "detail": error.message,
                "version": settings.app_version,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "database": "ok",
            "version": settings.app_version,
            "environment": settings.environment,
            "time": utcnow().isoformat(),
        },
    )
