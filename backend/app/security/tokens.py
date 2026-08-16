import base64
import hashlib
import hmac
import json
import time
from uuid import UUID


class SessionTokenError(ValueError):
    pass


def create_session_token(*, session_id: UUID, secret: str, ttl_seconds: int = 86_400) -> str:
    payload = {"sid": str(session_id), "exp": int(time.time()) + ttl_seconds}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def read_session_token(token: str, *, secret: str) -> UUID:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise SessionTokenError("Invalid session signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode()))
        if int(payload["exp"]) < int(time.time()):
            raise SessionTokenError("Session expired")
        return UUID(payload["sid"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SessionTokenError("Invalid session token") from exc


def create_action_token(
    *,
    secret: str,
    purpose: str,
    email: str,
    ttl_seconds: int = 3600,
    binding: str | None = None,
) -> str:
    """Sign a short-lived, single-purpose action token (email verify / password reset).

    ``binding``, when provided, ties the token to a caller-supplied value (e.g. a digest
    of the current password hash) so a token becomes invalid once that value changes.
    """
    payload = {
        "purpose": purpose,
        "email": email.lower(),
        "exp": int(time.time()) + ttl_seconds,
    }
    if binding is not None:
        payload["binding"] = binding
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def read_action_token(
    token: str,
    *,
    secret: str,
    purpose: str,
    email: str,
    binding: str | None = None,
) -> None:
    """Validate an action token; raises SessionTokenError when invalid/expired/mismatched."""
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise SessionTokenError("Invalid action signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode()))
        if int(payload["exp"]) < int(time.time()):
            raise SessionTokenError("Action expired")
        if payload.get("purpose") != purpose or payload.get("email", "").lower() != email.lower():
            raise SessionTokenError("Invalid action token")
        if binding is not None and not hmac.compare_digest(
            str(payload.get("binding", "")), binding
        ):
            raise SessionTokenError("Invalid action token")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SessionTokenError("Invalid action token") from exc
