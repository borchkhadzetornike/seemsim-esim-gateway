from __future__ import annotations

import time
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.utils import generate_request_id

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        idempotency_key = request.headers.get("Idempotency-Key", "")

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            idempotency_key=idempotency_key or None,
        )

        start = time.perf_counter()
        response: Any = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            status = response.status_code if response else 500
            logger.info(
                "request_completed",
                status_code=status,
                elapsed_ms=elapsed_ms,
            )
            if response:
                response.headers["X-Request-ID"] = request_id
