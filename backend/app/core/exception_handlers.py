from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError


def problem_details(
    *,
    status_code: int,
    title: str,
    detail: Any,
    instance: str,
    type_uri: str = "about:blank",
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Return an RFC 7807 Problem Details response."""
    body: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        media_type="application/problem+json",
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Render application errors as Problem Details."""
    return problem_details(
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        instance=str(request.url.path),
        type_uri=exc.type_uri,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Render HTTP exceptions as Problem Details."""
    return problem_details(
        status_code=exc.status_code,
        title="HTTP Error",
        detail=exc.detail,
        instance=str(request.url.path),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Render request validation errors as Problem Details."""
    return problem_details(
        status_code=422,
        title="Validation Error",
        detail="Request validation failed.",
        instance=str(request.url.path),
        type_uri="https://example.com/problems/validation-error",
        extra={"errors": exc.errors()},
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Render unexpected errors as Problem Details."""
    return problem_details(
        status_code=500,
        title="Internal Server Error",
        detail="An unexpected error occurred.",
        instance=str(request.url.path),
    )
