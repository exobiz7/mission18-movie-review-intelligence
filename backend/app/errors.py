"""Safe errors, tracing, bounded timing and response-header security defaults."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def request_id_of(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid.uuid4()))


def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    response = JSONResponse(
        {"error": {"code": code, "message": message, "request_id": request_id_of(request)}},
        status_code=status,
    )
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


def register_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        try:
            request.state.request_id = str(uuid.UUID(incoming))
        except (ValueError, TypeError, AttributeError):
            request.state.request_id = str(uuid.uuid4())
        start = time.perf_counter()

        def finish(response):
            response.headers["X-Request-ID"] = request.state.request_id
            response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.3f}"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cache-Control"] = "no-store"
            return response

        try:
            if request.method in {"POST", "PUT", "PATCH"}:
                # Content-Length is only an early check; also bound streamed bytes,
                # so chunked requests cannot bypass the limit.
                limit = 16_384
                declared = request.headers.get("Content-Length")
                if declared is not None:
                    try:
                        length = int(declared)
                    except ValueError:
                        length = -1
                    if length < 0:
                        response = error_response(
                            request,
                            400,
                            "INVALID_CONTENT_LENGTH",
                            "요청 크기를 확인할 수 없습니다.",
                        )
                        return finish(response)
                    if length > limit:
                        response = error_response(
                            request, 413, "BODY_TOO_LARGE", "요청 본문 크기가 제한을 초과했습니다."
                        )
                        return finish(response)
                body = bytearray()
                too_large = False
                async for chunk in request.stream():
                    if len(body) + len(chunk) > limit:
                        too_large = True
                        break
                    body.extend(chunk)
                if too_large:
                    response = error_response(
                        request, 413, "BODY_TOO_LARGE", "요청 본문 크기가 제한을 초과했습니다."
                    )
                else:
                    # Starlette's cached request forwards this same bounded body
                    # to FastAPI/Pydantic without consuming the stream twice.
                    request._body = bytes(body)
                    response = await call_next(request)
            else:
                response = await call_next(request)
        except Exception:
            # Stack details are logged server-side only. Never return raw DB/auth/model errors.
            logger.exception("Unhandled request failure req_id=%s", request.state.request_id)
            response = error_response(
                request, 500, "INTERNAL_ERROR", "요청 처리 중 문제가 발생했습니다."
            )
        return finish(response)

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
