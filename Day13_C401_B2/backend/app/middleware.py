from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from .auth.sessions import get_user_from_token
from .config import OPENAI_MODEL
from .logging_config import get_logger
from .pii import hash_user_id


def _extract_session_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "").strip()
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return token or None


def _resolve_log_context(request: Request) -> dict[str, str]:
    token = _extract_session_token(request)
    user = get_user_from_token(token) if token else None

    user_identifier = request.headers.get("x-user-id", "").strip()
    if user:
        user_identifier = user.get("student_id") or user.get("username") or user_identifier

    feature = request.url.path.strip("/") or "root"
    session_id = hash_user_id(token) if token else "anonymous"
    user_id_hash = hash_user_id(user_identifier) if user_identifier else "anonymous"

    return {
        "service": "api",
        "session_id": session_id,
        "user_id_hash": user_id_hash,
        "feature": feature,
        "model": OPENAI_MODEL,
    }


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach correlation context and emit request lifecycle logs."""

    async def dispatch(self, request: Request, call_next):
        clear_contextvars()

        inbound_request_id = request.headers.get("x-request-id", "").strip()
        correlation_id = inbound_request_id or f"req-{uuid.uuid4().hex[:8]}"
        logger = get_logger()
        log_context = _resolve_log_context(request)

        bind_contextvars(correlation_id=correlation_id, **log_context)
        request.state.correlation_id = correlation_id

        started = time.perf_counter()
        logger.info(
            "request_started",
            payload={"method": request.method, "path": request.url.path},
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "request_failed",
                error_type=type(exc).__name__,
                latency_ms=duration_ms,
                payload={"method": request.method, "path": request.url.path},
            )
            clear_contextvars()
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "request_completed",
            latency_ms=duration_ms,
            status_code=response.status_code,
            payload={"method": request.method, "path": request.url.path},
        )

        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(duration_ms)
        clear_contextvars()
        return response
