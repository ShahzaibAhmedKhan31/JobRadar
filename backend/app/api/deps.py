"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.constants import SortOption
from app.db.session import get_db
from app.sources.registry import SourceRegistry

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


def get_registry(request: Request) -> SourceRegistry:
    return request.app.state.registry


RegistryDep = Annotated[SourceRegistry, Depends(get_registry)]


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page")
        ] = DEFAULT_PAGE_SIZE,
    ) -> None:
        self.page = page
        self.page_size = page_size


PaginationDep = Annotated[Pagination, Depends()]


class JobSort:
    sort: Annotated[SortOption, Query(description="Sort order")] = SortOption.NEWEST


JobSortDep = Annotated[JobSort, Depends()]
