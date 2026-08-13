"""Prometheus metrics registry and an optional Langfuse trace hook."""

import base64
import logging
from datetime import UTC, datetime

import httpx
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from prometheus_client.exposition import REGISTRY

from app.core.config import get_settings

logger = logging.getLogger(__name__)

http_requests_total = Counter(
    "aria_http_requests_total",
    "HTTP requests handled",
    ["method", "path", "status"],
)
http_request_duration = Histogram(
    "aria_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)
ai_calls_total = Counter(
    "aria_ai_calls_total",
    "AI provider calls",
    ["kind", "model"],
)
ai_call_duration = Histogram(
    "aria_ai_call_duration_seconds",
    "AI call duration in seconds",
    ["kind"],
)


def normalize_path(path: str) -> str:
    segments = []
    for segment in path.split("/"):
        if not segment:
            continue
        if len(segment) == 36 and segment.count("-") == 4:
            segments.append("{id}")
        elif segment.isdigit():
            segments.append("{n}")
        else:
            segments.append(segment)
    return "/" + "/".join(segments)


def observe_request(*, method: str, path: str, status: int, duration_ms: int) -> None:
    label_path = normalize_path(path)
    http_requests_total.labels(method=method, path=label_path, status=str(status)).inc()
    http_request_duration.labels(method=method, path=label_path).observe(duration_ms / 1000.0)


def observe_ai_call(
    *,
    kind: str,
    model: str,
    duration_ms: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> None:
    ai_calls_total.labels(kind=kind, model=model).inc()
    ai_call_duration.labels(kind=kind).observe(duration_ms / 1000.0)
    _post_langfuse_trace(
        kind=kind,
        model=model,
        duration_ms=duration_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


def _langfuse_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.aria_langfuse_public_key
        and settings.aria_langfuse_secret_key
        and settings.aria_langfuse_host
    )


def _post_langfuse_trace(
    *,
    kind: str,
    model: str,
    duration_ms: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> None:
    if not _langfuse_configured():
        return
    settings = get_settings()
    host = settings.aria_langfuse_host.rstrip("/")
    payload = {
        "name": f"ai:{kind}",
        "input": {"model": model},
        "output": {},
        "metadata": {
            "duration_ms": duration_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    credentials = base64.b64encode(
        f"{settings.aria_langfuse_public_key}:{settings.aria_langfuse_secret_key}".encode()
    ).decode()
    try:
        httpx.post(
            f"{host}/api/public/traces",
            json=payload,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            timeout=2,
        )
    except Exception:
        logger.debug("langfuse trace post failed", exc_info=True)


def init_sentry() -> None:
    settings = get_settings()
    if not settings.aria_sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.aria_sentry_dsn,
            environment=settings.aria_env,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry telemetry enabled")
    except Exception:
        logger.exception("Sentry initialization failed")
