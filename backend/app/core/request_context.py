import logging
import time
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import observe_request

logger = logging.getLogger(__name__)

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        token = request_id_context.set(request_id)
        started = time.monotonic()
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "request method=%s path=%s status=%d duration_ms=%d request_id=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request_id,
            )
            observe_request(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        finally:
            request_id_context.reset(token)
