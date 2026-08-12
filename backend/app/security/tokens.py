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
