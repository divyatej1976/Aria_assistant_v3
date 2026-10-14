#!/usr/bin/env python3
"""Strict production preflight — bundled PostgreSQL only.

Fails fast if required secrets are missing or insecure defaults are used.
Never prints secret values; use *** redaction. Run before `docker compose config` and build.

Usage:
  python scripts/check_prod_secrets.py --strict --ai-tutoring --semantic-enabled --audio
  python scripts/check_prod_secrets.py --strict --ai-tutoring  # push deferred
  python scripts/check_prod_secrets.py --strict --audio --allow-local-tts  # local espeak-ng fallback (beta-only)
  python scripts/check_prod_secrets.py              # lenient: required vars only

Bundled deployment contract (do not attempt external DB until separate compose exists):
  POSTGRES_PASSWORD=<url-safe ^[A-Za-z0-9._~-]+$, not aria>
  DATABASE_URL=postgresql+psycopg://aria:<same password>@db:5432/aria
Preflight verifies both exist, db:5432 target, password not aria, and proves
DATABASE_URL embeds the exact same password as POSTGRES_PASSWORD — a typo
between the two would otherwise pass compose validation and then fail the
backend's database connection at runtime.
URL-safe generation: python -c "import secrets, string; print(secrets.token_urlsafe(32))"
then filter to [A-Za-z0-9._~-].
"""

import argparse
import math
import os
import re
import sys
import urllib.parse

URL_SAFE_RE = re.compile(r"^[A-Za-z0-9._~-]+$")

PLACEHOLDERS = {"app.example.com", "example.com"}


def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _valid_fernet_key(value: str) -> bool:
    """Stdlib-only Fernet key check: 32 urlsafe-base64-encoded bytes.

    Avoids importing cryptography so preflight stays dependency-free.
    """
    import base64

    if not value or len(value) != 44:
        return False
    try:
        raw = base64.urlsafe_b64decode(value.encode("ascii"))
    except Exception:
        return False
    return len(raw) == 32


def warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def require(env: dict[str, str], name: str) -> bool:
    if not env.get(name):
        error(f"{name} is required")
        return False
    return True


def _normalized_origin(url: str) -> str:
    """Normalize origin to scheme://host:effective_port for exact comparison."""
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        return ""
    scheme = (p.scheme or "").lower()
    try:
        host = (p.hostname or "").lower()
    except ValueError:
        return ""
    if not host:
        return ""
    try:
        port = p.port
    except ValueError:
        return ""
    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
        else:
            return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def validate_https_origin(name: str, value: str) -> bool:
    ok = True
    try:
        parsed = urllib.parse.urlparse(value)
    except ValueError:
        error(f"{name} must contain a valid hostname")
        return False
    if parsed.scheme != "https":
        error(f"{name} must use https:// (got {parsed.scheme or '(empty)'})")
        ok = False
    if parsed.path not in ("", "/"):
        error(f"{name} must be origin only, no path (/api) — got path {parsed.path}")
        ok = False
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        error(f"{name} must be a plain HTTPS origin (no query/fragment/userinfo)")
        ok = False
    # port and hostname can raise ValueError on malformed input
    try:
        _ = parsed.port
    except ValueError:
        error(f"{name} must contain a valid port")
        ok = False
    try:
        host = (parsed.hostname or "").lower()
    except ValueError:
        error(f"{name} must contain a valid hostname")
        ok = False
        host = ""
    if host in ("localhost", "127.0.0.1", "::1"):
        error(f"{name} must not be localhost (got {host})")
        ok = False
    if host in PLACEHOLDERS:
        error(f"{name} must not be placeholder {host} (always forbidden)")
        ok = False
    if not host:
        error(f"{name} must contain a host")
        ok = False
    return ok


def _password_mismatch(
    postgres_password: str | None, database_url: str | None
) -> str | None:
    """Return an error message when DATABASE_URL's embedded password does not
    exactly match POSTGRES_PASSWORD; None when they match or the comparison is
    not applicable (missing values / malformed URL are reported by their own
    checks). This mechanically couples the two secrets so a typo fails
    preflight instead of passing compose validation and failing at runtime.
    """
    if not postgres_password or not database_url:
        return None
    try:
        parsed = urllib.parse.urlparse(database_url)
    except ValueError:
        return None  # malformed URL is already reported by the DATABASE_URL checks
    if parsed.scheme != "postgresql+psycopg":
        return None  # scheme mismatch is already reported
    # urlparse does not percent-decode; psycopg (the actual consumer) does, so
    # decode before comparing. POSTGRES_PASSWORD is enforced url-safe, meaning
    # the operator password is raw and directly comparable once unquoted.
    raw = parsed.password
    embedded = urllib.parse.unquote(raw) if raw is not None else None
    if embedded is None or embedded != postgres_password:
        return (
            "DATABASE_URL password does not match POSTGRES_PASSWORD - the stack "
            "would start but the backend could not authenticate to the database. "
            "Set both from the same secret."
        )
    return None


def main(argv: list[str] | None = None, env: dict[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ARIA production preflight")
    parser.add_argument("--strict", action="store_true", help="Enforce unrestricted production policy")
    parser.add_argument("--ai-tutoring", action="store_true", help="AI tutoring required (Groq)")
    parser.add_argument("--byo-keys", action="store_true", help="Learner-supplied LLM keys required (BYO)")
    parser.add_argument("--semantic-enabled", action="store_true", help="Semantic retrieval required (embeddings)")
    parser.add_argument("--push-enabled", action="store_true", help="Web push required (VAPID)")
    parser.add_argument("--audio", action="store_true", help="Audio generation required (cloud TTS)")
    parser.add_argument(
        "--allow-local-tts",
        action="store_true",
        help="Accept container-local espeak-ng TTS instead of cloud (beta-only)",
    )
    args = parser.parse_args(argv)

    env = env if env is not None else os.environ
    failures = 0
    # Always-required
    for name in [
        "ARIA_SESSION_SECRET",
        "DATABASE_URL",
        "ARIA_PUBLIC_URL",
        "NEXT_PUBLIC_API_URL",
        "ARIA_CORS_ORIGINS",
        "ARIA_TRUSTED_HOSTS",
    ]:
        if not require(env, name):
            failures += 1
    # Bundled DB password required
    if not require(env, "POSTGRES_PASSWORD"):
        failures += 1
    else:
        pw = env["POSTGRES_PASSWORD"]
        if pw == "aria":
            error("POSTGRES_PASSWORD must not be default 'aria'")
            failures += 1
        if not URL_SAFE_RE.fullmatch(pw):
            error("POSTGRES_PASSWORD must be URL-safe ^[A-Za-z0-9._~-]+$ (no :/@# etc.)")
            failures += 1

    # DATABASE_URL checks — parse metadata, not substring; hardening for bundled contract
    db_url = env.get("DATABASE_URL", "")
    if db_url:
        try:
            p = urllib.parse.urlparse(db_url)
            if p.scheme != "postgresql+psycopg":
                error("DATABASE_URL must use scheme postgresql+psycopg")
                failures += 1
            elif (p.hostname or "").lower() != "db":
                error("DATABASE_URL must target bundled host db (external DB not yet supported)")
                failures += 1
            else:
                try:
                    port = p.port
                except ValueError:
                    error("DATABASE_URL has invalid port")
                    failures += 1
                else:
                    if port != 5432:
                        error("DATABASE_URL must target bundled db:5432 (external DB not yet supported)")
                        failures += 1
                # bundled contract hardening: username and database
                if (p.username or "") != "aria":
                    error("DATABASE_URL must use username aria")
                    failures += 1
                # p.path is "/aria" for bundled; reject other dbs
                db_name = (p.path or "").lstrip("/")
                if db_name != "aria":
                    error("DATABASE_URL must use database /aria")
                    failures += 1
        except ValueError as e:
            error(f"DATABASE_URL is malformed: {e}")
            failures += 1

    # Mechanically couple the two DB secrets: a typo between POSTGRES_PASSWORD
    # and the password embedded in DATABASE_URL would pass the per-variable
    # checks above and only fail at backend runtime.
    mismatch = _password_mismatch(env.get("POSTGRES_PASSWORD"), env.get("DATABASE_URL"))
    if mismatch:
        error(mismatch)
        failures += 1

    # Public URLs strict
    for name in ["ARIA_PUBLIC_URL", "NEXT_PUBLIC_API_URL"]:
        val = env.get(name, "")
        if val and not validate_https_origin(name, val):
            failures += 1
    # ARIA_PUBLIC_URL and NEXT_PUBLIC_API_URL- specific: check CORS etc in strict
    if args.strict:
        # CORS — every entry independently validated as HTTPS origin
        cors = env.get("ARIA_CORS_ORIGINS", "")
        if cors:
            origins = [o.strip() for o in cors.split(",") if o.strip()]
            if "*" in origins:
                error("ARIA_CORS_ORIGINS must not contain *")
                failures += 1
            for o in origins:
                # Reuse same validator as public URLs
                # (https, host, no path/query/fragment/userinfo, not placeholder/localhost)
                if not validate_https_origin(f"ARIA_CORS_ORIGINS entry {o}", o):
                    failures += 1
            # ARIA_PUBLIC_URL origin must be exact member of CORS
            # (moved outside loop to avoid duplicates)
            pub = env.get("ARIA_PUBLIC_URL", "")
            if pub:
                pub_origin = _normalized_origin(pub)
                cors_origins_normalized = {
                    _normalized_origin(o) for o in origins
                }
                if pub_origin and pub_origin not in cors_origins_normalized:
                    error(
                        f"ARIA_PUBLIC_URL {pub} must be present as exact"
                        " origin in ARIA_CORS_ORIGINS — browser will be blocked"
                    )
                    failures += 1
        # Trusted hosts: must contain public host + localhost,127.0.0.1, allow extras, reject *, scheme
        trusted = env.get("ARIA_TRUSTED_HOSTS", "")
        if trusted:
            hosts = [h.strip() for h in trusted.split(",") if h.strip()]
            if "*" in hosts:
                error("ARIA_TRUSTED_HOSTS must not contain *")
                failures += 1
            if not trusted.strip():
                error("ARIA_TRUSTED_HOSTS must not be empty")
                failures += 1
            for h in hosts:
                if "://" in h:
                    error(f"ARIA_TRUSTED_HOSTS must not contain scheme ({h})")
                    failures += 1
            lowers = {h.lower() for h in hosts}
            if "localhost" not in lowers or "127.0.0.1" not in lowers:
                error("ARIA_TRUSTED_HOSTS must contain localhost,127.0.0.1 for container health checks")
                failures += 1
            pub = env.get("ARIA_PUBLIC_URL", "")
            if pub:
                try:
                    pub_host = (urllib.parse.urlparse(pub).hostname or "").lower()
                except ValueError:
                    # malformed ARIA_PUBLIC_URL already reported by validate_https_origin; skip host-dependent checks
                    pub_host = ""
                else:
                    if pub_host and pub_host not in lowers:
                        error(f"ARIA_TRUSTED_HOSTS must contain actual public host {pub_host} from ARIA_PUBLIC_URL")
                        failures += 1
                    if not pub_host or pub_host in ("localhost", "127.0.0.1", "::1"):
                        error("ARIA_PUBLIC_URL host must be public domain, not localhost")
                        failures += 1
        # Numeric deployment-controlled settings — forwarded by docker-compose.prod.yml
        # ARIA_API_PREFIX intentionally not forwarded (routes hardcode /api/v1); validated here as inactive
        budget = env.get("ARIA_AI_MONTHLY_BUDGET_USD", "0")
        try:
            b = float(budget)
            if not math.isfinite(b) or b < 0:
                raise ValueError
        except (ValueError, TypeError):
            error(f"ARIA_AI_MONTHLY_BUDGET_USD must be finite number >=0 (got {budget})")
            failures += 1
        else:
            # Unrestricted production: 0 = unlimited — document as approved or set >0
            if args.strict and b == 0:
                warn(
                    "ARIA_AI_MONTHLY_BUDGET_USD=0 means unlimited AI spending"
                    " — ensure this is an approved production choice (set >0 to cap cost)"
                )
        for name, default in [
            ("ARIA_RATE_LIMIT_REQUESTS", "10"),
            ("ARIA_RATE_LIMIT_WINDOW_SECONDS", "60"),
            ("ARIA_REMINDER_CHECK_INTERVAL_MINUTES", "60"),
            ("ARIA_AUDIO_QUEUE_INTERVAL_SECONDS", "30"),
            ("ARIA_IDEMPOTENCY_TTL_SECONDS", "3600"),
        ]:
            raw = env.get(name, default)
            try:
                # strict positive int, no floats, no extra chars
                if str(int(raw)) != str(raw).strip():
                    raise ValueError
                iv = int(raw)
                if iv <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                error(f"{name} must be positive integer (got {raw})")
                failures += 1
        # Low-priority forwarded settings — validate format when supplied
        tts_provider = env.get("ARIA_TTS_PROVIDER", "auto")
        if tts_provider not in ("auto", "cloud", "local"):
            error(f"ARIA_TTS_PROVIDER must be one of auto, cloud, local (got {tts_provider})")
            failures += 1
        log_level = env.get("ARIA_LOG_LEVEL", "INFO")
        if log_level.upper() not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"):
            error(f"ARIA_LOG_LEVEL must be a recognized level (got {log_level})")
            failures += 1
        smtp_tls = env.get("SMTP_USE_TLS", "true")
        if smtp_tls.lower() not in ("true", "false", "1", "0", "yes", "no", "on", "off", "t", "f", "y", "n"):
            error(f"SMTP_USE_TLS must be a valid boolean (got {smtp_tls})")
            failures += 1
        emb_base = env.get("ARIA_EMBEDDING_BASE_URL", "")
        if emb_base:
            # Must be valid HTTPS URL when supplied (allow path, e.g. https://api.openai.com/v1)
            try:
                p = urllib.parse.urlparse(emb_base)
                if p.scheme != "https":
                    raise ValueError("scheme must be https")
                if p.username or p.password:
                    raise ValueError("must not contain userinfo")
                if p.query or p.fragment:
                    raise ValueError("must not contain query/fragment")
                host = (p.hostname or "").lower()
                if not host or host in PLACEHOLDERS or host in ("localhost", "127.0.0.1", "::1"):
                    raise ValueError("invalid host")
                _ = p.port  # validates port
                if p.hostname is None:
                    raise ValueError("invalid hostname")
            except ValueError as e:
                error(
                    f"ARIA_EMBEDDING_BASE_URL must be a valid HTTPS URL"
                    f" when supplied: {e}"
                )
                failures += 1

    # Feature-gated strict requirements
    if args.strict:
        # Backups are on by default in prod compose: dumps hold password
        # hashes + PII, so at-rest encryption is mandatory unless the
        # operator explicitly disables scheduled backups.
        backups_enabled = env.get("ARIA_BACKUP_ENABLED", "true").lower() not in (
            "false", "0", "no", "off",
        )
        if backups_enabled:
            backup_key = env.get("ARIA_BACKUP_ENCRYPTION_KEY", "")
            if not backup_key:
                error("ARIA_BACKUP_ENCRYPTION_KEY is required (backups hold PII); "
                      "generate one like a Fernet key or set ARIA_BACKUP_ENABLED=false")
                failures += 1
            elif not _valid_fernet_key(backup_key):
                error("ARIA_BACKUP_ENCRYPTION_KEY must be a valid Fernet key "
                      "(32 urlsafe-base64 bytes)")
                failures += 1
        # SMTP required for unrestricted (email verification/reset active)
        if not env.get("SMTP_HOST"):
            error("SMTP_HOST is required for unrestricted prod (email verification/password reset)")
            failures += 1
        else:
            smtp_from = env.get("SMTP_FROM", "")
            if not smtp_from:
                error("SMTP_FROM is required when SMTP_HOST is set")
                failures += 1
            elif "@example.com" in smtp_from.lower() or "@aria.local" in smtp_from.lower():
                error("SMTP_FROM must not use a placeholder sender")
                failures += 1
            port = env.get("SMTP_PORT", "587")
            try:
                p = int(port)
                if not (1 <= p <= 65535):
                    raise ValueError
            except ValueError:
                error(f"SMTP_PORT must be valid port (got {port})")
                failures += 1
            # username/password only if provider needs auth — warn, not fail, unless both missing and host implies auth
            # Documented as provider-specific; we do not infer.
        if args.ai_tutoring and not env.get("GROQ_API_KEY"):
            error("GROQ_API_KEY is required when --ai-tutoring")
            failures += 1
        if args.byo_keys and not env.get("ARIA_LLM_KEYS_ENCRYPTION_KEY"):
            error("ARIA_LLM_KEYS_ENCRYPTION_KEY is required when --byo-keys")
            failures += 1
        if args.byo_keys:
            if not _valid_fernet_key(env.get("ARIA_LLM_KEYS_ENCRYPTION_KEY", "")):
                error("ARIA_LLM_KEYS_ENCRYPTION_KEY must be a valid Fernet key "
                      "(generate with scripts/generate_llm_keys_key.py)")
                failures += 1
            old_key = env.get("ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD", "")
            if old_key and not _valid_fernet_key(old_key):
                error("ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD must be a valid Fernet key")
                failures += 1
            models = [m.strip() for m in env.get(
                "ARIA_LLM_ALLOWED_MODELS",
                "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b,"
                "llama-3.3-70b-versatile,llama-3.1-8b-instant").split(",") if m.strip()]
            if not models:
                error("ARIA_LLM_ALLOWED_MODELS must list at least one model")
                failures += 1
            try:
                per_user = float(env.get("ARIA_LLM_PER_USER_BUDGET_USD", "0") or "0")
                if not math.isfinite(per_user) or per_user < 0:
                    raise ValueError
            except ValueError:
                error("ARIA_LLM_PER_USER_BUDGET_USD must be finite and non-negative")
                failures += 1
            try:
                reserve = int(env.get("ARIA_LLM_COMPLETION_RESERVE_TOKENS", "512") or "512")
                if reserve < 0:
                    raise ValueError
            except ValueError:
                error("ARIA_LLM_COMPLETION_RESERVE_TOKENS must be a non-negative integer")
                failures += 1
            if env.get("ARIA_RATE_LIMIT_BACKEND", "memory") not in ("memory", "db"):
                error("ARIA_RATE_LIMIT_BACKEND must be 'memory' or 'db'")
                failures += 1
        if args.semantic_enabled and not env.get("ARIA_EMBEDDING_API_KEY"):
            error("ARIA_EMBEDDING_API_KEY is required when --semantic-enabled")
            failures += 1
        if args.semantic_enabled:
            dim = env.get("ARIA_EMBEDDING_DIM", "768")
            if str(dim) != "768":
                error("ARIA_EMBEDDING_DIM must be 768 for current Vector(768) schema; migrate first if changing")
                failures += 1
        if args.push_enabled:
            if not env.get("ARIA_VAPID_PUBLIC_KEY") or not env.get("ARIA_VAPID_PRIVATE_KEY"):
                error("ARIA_VAPID_PUBLIC_KEY and ARIA_VAPID_PRIVATE_KEY required when --push-enabled")
                failures += 1
        if args.audio:
            # Unrestricted prod must not rely on the unproven container-local
            # fallback: require a cloud TTS provider (Groq rides on
            # GROQ_API_KEY, no separate key) unless the operator explicitly
            # accepts the local espeak-ng path as beta-only.
            has_cloud_tts = bool(env.get("GROQ_API_KEY") or env.get("ARIA_TTS_API_KEY"))
            if not has_cloud_tts and not args.allow_local_tts:
                error(
                    "Audio required (--audio): no cloud TTS provider configured. "
                    "Set GROQ_API_KEY or ARIA_TTS_API_KEY, or pass "
                    "--allow-local-tts to accept the container-local espeak-ng "
                    "fallback (beta-only)."
                )
                failures += 1
            nxt_pub = env.get("NEXT_PUBLIC_VAPID_PUBLIC_KEY", "")
            pub = env.get("ARIA_VAPID_PUBLIC_KEY", "")
            if pub and nxt_pub and pub != nxt_pub:
                error("NEXT_PUBLIC_VAPID_PUBLIC_KEY must match ARIA_VAPID_PUBLIC_KEY")
                failures += 1
    else:
        # lenient mode: warnings only
        if not env.get("SMTP_HOST"):
            warn("SMTP_HOST empty — emails will be logged, not delivered")
        if not env.get("GROQ_API_KEY"):
            warn("GROQ_API_KEY empty — tutoring falls back to deterministic")
        if not env.get("ARIA_VAPID_PUBLIC_KEY"):
            warn("VAPID keys empty — web push disabled (graceful)")

    # Optional operational warnings
    if args.strict:
        if not env.get("ARIA_SENTRY_DSN"):
            warn("ARIA_SENTRY_DSN empty — Sentry disabled")
        if not env.get("ARIA_LANGFUSE_PUBLIC_KEY"):
            warn("Langfuse disabled")

    # Secret-safe: never print values, only names
    if failures:
        print(f"Preflight failed: {failures} error(s)", file=sys.stderr)
        return 1
    print("Preflight passed (strict)" if args.strict else "Preflight passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
