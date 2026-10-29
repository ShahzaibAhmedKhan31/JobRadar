"""Shortlist endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import DbSession, PaginationDep, RegistryDep
from app.core.constants import Priority
from app.schemas.common import Page
from app.schemas.shortlist import (
    ShortlistCreate,
    ShortlistRead,
    ShortlistUpdate,
    shortlist_to_read,
)
from app.services import shortlist as shortlist_service

router = APIRouter(prefix="/shortlist", tags=["shortlist"])


@router.get("", response_model=Page[ShortlistRead], summary="List shortlisted jobs")
def list_shortlist(
    db: DbSession,
    registry: RegistryDep,
    pagination: PaginationDep,
    sources: Annotated[list[str] | None, Query()] = None,
    priority: Annotated[Priority | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sort: Annotated[str, Query(pattern="^(newest|oldest|priority)$")] = "newest",
) -> Page[ShortlistRead]:
    if sources:
        unknown = set(sources) - registry.known_keys()
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown source key(s): {', '.join(sorted(unknown))}",
            )
    filters = shortlist_service.ShortlistFilters(
        sources=sources or [],
        priority=priority,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort=sort,
    )
    entries, total = shortlist_service.list_shortlist(
        db, filters, page=pagination.page, page_size=pagination.page_size
    )
    items = [shortlist_to_read(entry) for entry in entries]
    return Page.build(
        items, total=total, page=pagination.page, page_size=pagination.page_size
    )


@router.post(
    "/{job_id}",
    response_model=ShortlistRead,
    summary="Shortlist a job",
    status_code=status.HTTP_201_CREATED,
)
def create_shortlist_entry(
    job_id: uuid.UUID,
    db: DbSession,
    response: Response,
    payload: ShortlistCreate | None = None,
) -> ShortlistRead:
    payload = payload or ShortlistCreate()
    entry, created = shortlist_service.add_to_shortlist(
        db,
        job_id,
        priority=payload.priority,
        notes=payload.normalized_notes(),
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return shortlist_to_read(entry)


@router.patch(
    "/{job_id}", response_model=ShortlistRead, summary="Update shortlist priority/notes"
)
def update_shortlist_entry(
    job_id: uuid.UUID,
    payload: ShortlistUpdate,
    db: DbSession,
) -> ShortlistRead:
    changes = payload.model_dump(exclude_unset=True)
    if "notes" in changes and isinstance(changes["notes"], str):
        changes["notes"] = changes["notes"].strip() or None
    entry = shortlist_service.update_shortlist(db, job_id, changes)
    return shortlist_to_read(entry)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a job from the shortlist",
)
def delete_shortlist_entry(job_id: uuid.UUID, db: DbSession) -> Response:
    shortlist_service.remove_from_shortlist(db, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
