"""Application tracker endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DbSession, PaginationDep
from app.core.constants import ApplicationStatus
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    application_to_read,
)
from app.schemas.common import Page
from app.services import applications as application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=Page[ApplicationRead], summary="List tracked applications")
def list_applications(
    db: DbSession,
    pagination: PaginationDep,
    application_status: Annotated[
        list[ApplicationStatus] | None, Query(alias="status")
    ] = None,
    company: Annotated[str | None, Query(max_length=200)] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    sort: Annotated[
        str, Query(pattern="^(newest|oldest|updated|company)$")
    ] = "newest",
) -> Page[ApplicationRead]:
    filters = application_service.ApplicationFilters(
        statuses=application_status or [],
        company=company,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    items, total = application_service.list_applications(
        db, filters, page=pagination.page, page_size=pagination.page_size
    )
    return Page.build(
        [application_to_read(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start tracking an application",
)
def create_application(payload: ApplicationCreate, db: DbSession) -> ApplicationRead:
    application = application_service.create_application(db, payload)
    return application_to_read(application)


@router.get(
    "/{application_id}", response_model=ApplicationRead, summary="Retrieve an application"
)
def get_application(application_id: uuid.UUID, db: DbSession) -> ApplicationRead:
    application = application_service.get_application(db, application_id)
    return application_to_read(application)


@router.patch(
    "/{application_id}",
    response_model=ApplicationRead,
    summary="Update status, notes or dates",
)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    db: DbSession,
) -> ApplicationRead:
    provided = set(payload.model_dump(exclude_unset=True).keys())
    application = application_service.update_application(
        db, application_id, payload, provided_fields=provided
    )
    return application_to_read(application)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tracking record",
)
def delete_application(application_id: uuid.UUID, db: DbSession) -> Response:
    application_service.delete_application(db, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
