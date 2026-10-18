"""Cookie session helpers and a double-submit CSRF guard.

Sessions are issued as an HttpOnly cookie (`aria_session`) backed by the same
signed token used by the bearer scheme. A readable `aria_csrf` cookie carries
the double-submit token: state-changing requests that authenticate via cookie
must echo it in the `X-CSRF-Token` header. Bearer-authenticated requests are
exempt because the bearer token itself is the secret.
"""

import hmac
import secrets

from app.core.config import get_settings

SESSION_COOKIE = "aria_session"
CSRF_COOKIE = "aria_csrf"
CSRF_HEADER = "X-CSRF-Token"
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
SESSION_TTL_SECONDS = 86_400
# Unauthenticated credential endpoints: the same-site cookie policy already
# blocks login CSRF, and there is no existing session to protect. Password
# reset is additionally protected by a signed, email-bound token.
PUBLIC_MUTATING_PATHS = frozenset(
    {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/password-reset/request",
        "/api/v1/auth/password-reset/confirm",
        "/api/v1/auth/verify-email/confirm",
    }
)


def _secure() -> bool:
    return get_settings().aria_env == "production"


def set_auth_cookies(response, token: str) -> None:
    secure = _secure()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="strict",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        # Same lifetime as the session: the frontend reads this cookie to know
        # a session exists, and a browser-session cookie would vanish on close.
        max_age=SESSION_TTL_SECONDS,
        httponly=False,
        samesite="strict",
        secure=secure,
        path="/",
    )


def clear_auth_cookies(response) -> None:
    secure = _secure()
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=secure, httponly=True, samesite="strict"
    )
    response.delete_cookie(
        CSRF_COOKIE, path="/", secure=secure, httponly=False, samesite="strict"
    )


def _cookie_map(cookie_header: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in cookie_header.split(";"):
        key, _, value = part.strip().partition("=")
        if key:
            values[key] = value
    return values


async def _send_json(send, status_code: int, detail: str) -> None:
    body = f'{{"detail": "{detail}"}}'.encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class CSRFMiddleware:
    """Reject cookie-authenticated state changes without a matching CSRF token."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        path = scope.get("path", "")
        method = scope.get("method", "")
        cookie_header = headers.get("cookie", "")
        cookies = _cookie_map(cookie_header)
        if (
            method in MUTATING_METHODS
            and path not in PUBLIC_MUTATING_PATHS
            and SESSION_COOKIE in cookies
            # Exempt only genuine Bearer credentials: the auth dependency
            # falls back to cookie auth for any other Authorization scheme,
            # and those requests still require a CSRF token.
            and not headers.get("authorization", "").startswith("Bearer ")
        ):
            token = cookies.get(CSRF_COOKIE, "")
            submitted = headers.get("x-csrf-token", "")
            # Bytes comparison: str compare_digest raises TypeError on
            # non-ASCII input, which would turn a bad token into a 500.
            valid = False
            if token and submitted:
                try:
                    valid = hmac.compare_digest(
                        token.encode("utf-8"), submitted.encode("utf-8")
                    )
                except Exception:
                    valid = False
            if not valid:
                await _send_json(
                    send, 403, "CSRF token missing or invalid"
                )
                return
        await self.app(scope, receive, send)
