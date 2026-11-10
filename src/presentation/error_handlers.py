"""Převod doménových výjimek byznys vrstvy na HTTP odpovědi."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from src.business.exceptions import (
    DomainError,
    NotFoundError,
    BusinessRuleError,
    ConflictError,
    PermissionDeniedError,
    AuthenticationError,
    AccountDisabledError,
)

STATUS_BY_ERROR = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    BusinessRuleError: status.HTTP_400_BAD_REQUEST,
    ConflictError: status.HTTP_409_CONFLICT,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AccountDisabledError: status.HTTP_403_FORBIDDEN,
}


def _status_for(exc: DomainError) -> int:
    for error_type, code in STATUS_BY_ERROR.items():
        if isinstance(exc, error_type):
            return code
    return status.HTTP_400_BAD_REQUEST


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    code = _status_for(exc)
    headers = {"WWW-Authenticate": "Bearer"} if code == status.HTTP_401_UNAUTHORIZED else None
    return JSONResponse(status_code=code, content={"detail": exc.message}, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
