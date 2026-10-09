"""Stable safe errors, request-id handling and validation-error normalization."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def request_id_of(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid.uuid4()))


def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, "request_id": request_id_of(request)}},
        status_code=status,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        try:
            request.state.request_id = str(uuid.UUID(incoming))
        except (ValueError, TypeError, AttributeError):
            request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        return error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        _ = exc
        return error_response(
            request, 422, "VALIDATION_ERROR", "입력 형식과 값 범위를 확인해 주세요."
        )
