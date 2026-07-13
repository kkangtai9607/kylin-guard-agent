from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from backend.app.api.router import router
from backend.app.core.config import get_config
from backend.app.core.errors import AppError, ErrorCode
from backend.app.core.inspection_service import capture_inspection
from backend.app.core.snapshot_scheduler import PeriodicSnapshotService
from backend.app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    config = get_config()

    async def scheduled_capture() -> None:
        def capture() -> None:
            with SessionLocal() as db:
                capture_inspection(db)

        await asyncio.to_thread(capture)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service = PeriodicSnapshotService(config.snapshot_interval_seconds, scheduled_capture)
        app.state.snapshot_service = service
        if config.snapshot_scheduler_enabled:
            service.start()
        try:
            yield
        finally:
            await service.stop()

    app = FastAPI(title=config.name, version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:128]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return error_response(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, _: RequestValidationError) -> JSONResponse:
        return error_response(request, 422, ErrorCode.VALIDATION_ERROR, "request validation failed")

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled request error: %s %s", request.method, request.url.path, exc_info=exc)
        return error_response(request, 500, ErrorCode.INTERNAL_ERROR, "internal server error")

    app.include_router(router)
    return app


def error_response(
    request: Request,
    status_code: int,
    code: ErrorCode,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    config = get_config()
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "data": None,
            "error": {"code": code, "message": message, "details": details},
            "meta": {"mode": config.mode, "is_demo": config.mode == "DEMO"},
        },
    )


app = create_app()
