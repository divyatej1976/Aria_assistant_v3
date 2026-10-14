import logging
import re

from app.core.config import get_settings

_SECRETS: tuple[str, ...] = ()
_SECRET_FIELDS = (
    "groq_api_key", "aria_session_secret", "supabase_jwt_secret", "supabase_anon_key",
    "aria_tts_api_key", "aria_stt_api_key", "aria_embedding_api_key", "smtp_password",
    "aria_llm_keys_encryption_key", "aria_llm_keys_encryption_key_old",
    "aria_backup_encryption_key", "aria_vapid_private_key", "aria_langfuse_secret_key",
    "aria_metrics_token", "aria_sentry_dsn",
)


def redact_log_text(value: str) -> str:
    for secret in _SECRETS:
        value = value.replace(secret, "[REDACTED]")
    value = re.sub(r"\b(?:gsk_|sk-)[A-Za-z0-9_-]{8,}", "[REDACTED]", value)
    value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._-]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)((?:api[_-]?key|password|token)=)[^&\s'\"]+", r"\1[REDACTED]", value)
    value = re.sub(r"(://)[^/\s@]+@", r"\1[REDACTED]@", value)
    return value


def configure_logging() -> None:
    global _SECRETS
    settings = get_settings()
    _SECRETS = tuple(
        value for field in _SECRET_FIELDS
        if isinstance(value := getattr(settings, field, None), str) and value
    )
    factory = logging.getLogRecordFactory()
    if not getattr(factory, "aria_redaction", False):
        def safe_record(*args, **kwargs):
            record = factory(*args, **kwargs)
            # Formatting an exception argument leaks its body even without
            # exc_info. Sanitize before getMessage, including mapping formats.
            def safe_argument(value):
                return f"error_type={type(value).__name__}" if isinstance(value, BaseException) else value

            if isinstance(record.args, tuple):
                record.args = tuple(safe_argument(value) for value in record.args)
            elif isinstance(record.args, dict):
                record.args = {key: safe_argument(value) for key, value in record.args.items()}
            if isinstance(record.msg, BaseException):
                record.msg = safe_argument(record.msg)
            if record.name == "uvicorn.access" and isinstance(record.args, tuple):
                # AccessFormatter unpacks the five arguments to construct its
                # request/status fields. Preserve their shape and numeric types.
                record.args = tuple(
                    redact_log_text(value) if isinstance(value, str) else value
                    for value in record.args
                )
                record.msg = redact_log_text(str(record.msg))
                record.exc_info = None
                record.exc_text = None
                return record
            message = redact_log_text(record.getMessage())
            if record.exc_info:
                # Provider exceptions may contain headers, response bodies or
                # SQL parameters. Keep diagnostic type/correlation, not raw text.
                message += f" error_type={record.exc_info[0].__name__}"
                record.exc_info = None
                record.exc_text = None
            record.msg = message
            record.args = ()
            return record
        safe_record.aria_redaction = True
        logging.setLogRecordFactory(safe_record)
    logging.basicConfig(
        level=getattr(logging, settings.aria_log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
