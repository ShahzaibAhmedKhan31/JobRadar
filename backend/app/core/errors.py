"""Domain errors mapped to HTTP responses in ``app.main``."""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected, user-facing failures."""

    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class UnprocessableError(AppError):
    status_code = 422
    code = "unprocessable_entity"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
