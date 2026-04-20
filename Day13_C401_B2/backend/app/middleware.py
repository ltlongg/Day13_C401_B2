from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Scaffold middleware cho task Logging & Security cua Lab13."""

    async def dispatch(self, request: Request, call_next):
        # TODO(A1): Xoa contextvars cu de tranh leak giua cac request.
        clear_contextvars()

        # TODO(A1): Uu tien lay x-request-id tu client, neu khong co thi tao moi.
        inbound_request_id = request.headers.get("x-request-id", "").strip()
        correlation_id = inbound_request_id or f"req-{uuid.uuid4().hex[:8]}"

        # TODO(A2): Bind them cac context khac neu nhom muon enrich log tai day.
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)

        # TODO(A2): Co the them x-response-time-ms neu nhom muon dung cho debug nhanh.
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(duration_ms)
        return response
