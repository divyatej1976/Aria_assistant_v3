"""BYO learner LLM keys (Step 4).

- Ciphertext at rest (Fernet) with a dedicated encryption key that is
  independent of ARIA_SESSION_SECRET, so session-secret rotation never
  invalidates stored learner keys.
- Rotation: ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD decrypts legacy rows;
  all new encryptions use the primary key.
- API/exports/logs never carry plaintext: only `key_hint` ("...last4").
- Provider allowlist: groq only. Model allowlist from settings.
- Precedence: learner key -> global GROQ_API_KEY -> deterministic fallback.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import LearnerLLMKey

PROVIDER_GROQ = "groq"


def generate_encryption_key() -> str:
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode("utf-8")


def _fernet_candidates():
    from cryptography.fernet import Fernet

    settings = get_settings()
    candidates = []
    for raw in (
        getattr(settings, "aria_llm_keys_encryption_key", None),
        getattr(settings, "aria_llm_keys_encryption_key_old", None),
    ):
        if not raw:
            continue
        try:
            candidates.append(Fernet(raw.encode("utf-8")))
        except Exception as exc:
            raise ValidationError("LLM key encryption is misconfigured") from exc
    return candidates


def _primary_fernet():
    from cryptography.fernet import Fernet

    raw = getattr(get_settings(), "aria_llm_keys_encryption_key", None)
    if not raw:
        raise ValidationError(
            "Personal LLM keys are not enabled on this deployment."
        )
    try:
        return Fernet(raw.encode("utf-8"))
    except Exception as exc:
        raise ValidationError("LLM key encryption is misconfigured") from exc


def encrypt_key(plaintext: str) -> str:
    return _primary_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_key(token: str) -> str:
    from cryptography.fernet import InvalidToken

    candidates = _fernet_candidates()
    if not candidates:
        raise ValidationError(
            "Personal LLM keys are not enabled on this deployment."
        )
    for fernet in candidates:
        try:
            return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            continue
    raise ValidationError("Stored LLM key could not be decrypted.")


def reencrypt_with_primary(db: Session) -> dict[str, int]:
    """Rotation job: rewrite every legacy-ciphertext row with the primary key.

    Run after promoting a new ARIA_LLM_KEYS_ENCRYPTION_KEY and keeping the
    previous value in ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD. Rows already under
    the primary key are untouched. Returns
    {"total": N, "reencrypted": M, "failed": K}; failed rows (decryptable by
    neither key) are left in place for operator inspection, never deleted.
    Only after `failed == 0` and a second run reports `reencrypted == 0`
    is it safe to drop the `_OLD` key.
    """
    from cryptography.fernet import InvalidToken

    primary = _primary_fernet()
    candidates = _fernet_candidates()
    summary = {"total": 0, "reencrypted": 0, "failed": 0}
    for row in db.scalars(select(LearnerLLMKey)).all():
        summary["total"] += 1
        try:
            primary.decrypt(row.encrypted_key.encode("utf-8"))
            continue  # already under the primary key
        except InvalidToken:
            pass
        plaintext: str | None = None
        for fernet in candidates[1:]:
            try:
                plaintext = fernet.decrypt(row.encrypted_key.encode("utf-8")).decode("utf-8")
                break
            except InvalidToken:
                continue
        if plaintext is None:
            summary["failed"] += 1
            continue
        row.encrypted_key = primary.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        db.add(row)
        summary["reencrypted"] += 1
    db.commit()
    return summary


def key_hint(plaintext: str) -> str:
    tail = plaintext[-4:] if len(plaintext) >= 4 else "****"
    return f"...{tail}"


def validate_key_format(*, provider: str, key: str) -> None:
    if provider != PROVIDER_GROQ:
        raise ValidationError("Unsupported LLM provider")
    if not key.startswith("gsk_") or len(key) < 20 or len(key) > 200:
        raise ValidationError("Invalid Groq API key format")
    if any(char.isspace() for char in key):
        raise ValidationError("Invalid Groq API key format")


def validate_model(model: str | None) -> None:
    if model is None:
        return
    allowed = get_settings().llm_allowed_models
    if model not in allowed:
        raise ValidationError(f"Model '{model}' is not allowed")


def set_key(
    db: Session, *, owner_id: UUID, key: str, model: str | None = None
) -> LearnerLLMKey:
    validate_key_format(provider=PROVIDER_GROQ, key=key)
    validate_model(model)
    existing = db.scalar(
        select(LearnerLLMKey).where(LearnerLLMKey.owner_id == owner_id)
    )
    if existing is None:
        existing = LearnerLLMKey(
            owner_id=owner_id,
            provider=PROVIDER_GROQ,
            encrypted_key=encrypt_key(key),
            key_hint=key_hint(key),
            model=model,
        )
        db.add(existing)
    else:
        existing.provider = PROVIDER_GROQ
        existing.encrypted_key = encrypt_key(key)
        existing.key_hint = key_hint(key)
        existing.model = model
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def get_status(db: Session, *, owner_id: UUID) -> dict:
    row = db.scalar(select(LearnerLLMKey).where(LearnerLLMKey.owner_id == owner_id))
    if row is None:
        return {"configured": False, "usable": False, "issue": None,
                "provider": None, "model": None, "hint": None}
    issue = None
    try:
        usable = bool(decrypt_key(row.encrypted_key))
    except ValidationError:
        usable = False
        issue = "credential_unreadable"
    if row.provider != PROVIDER_GROQ or (row.model and row.model not in get_settings().llm_allowed_models):
        usable = False
        issue = "configuration_unsupported"
    return {
        "configured": True,
        "usable": usable,
        "issue": issue,
        "provider": row.provider,
        "model": row.model,
        "hint": row.key_hint,
    }


def delete_key(db: Session, *, owner_id: UUID) -> bool:
    row = db.scalar(select(LearnerLLMKey).where(LearnerLLMKey.owner_id == owner_id))
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def get_capabilities(db: Session, *, owner_id: UUID) -> dict:
    settings = get_settings()
    key, model, source = resolve_credential(db, owner_id=owner_id)
    try:
        _primary_fernet()
        personal_keys_enabled = True
    except ValidationError:
        personal_keys_enabled = False
    deployment_key = bool(settings.groq_api_key)
    return {
        "credential_source": source,
        "tutor_configured": bool(key),
        "provider_verified": False,
        "model": model,
        "allowed_models": settings.llm_allowed_models,
        "personal_keys_enabled": personal_keys_enabled,
        "personal_key": get_status(db, owner_id=owner_id),
        "speech_to_text_configured": deployment_key or bool(getattr(settings, "aria_stt_api_key", None)),
        "cloud_speech_configured": deployment_key or bool(getattr(settings, "aria_tts_api_key", None)),
        "audio_credential_scope": "deployment",
    }


def resolve_credential(
    db: Session, *, owner_id: UUID
) -> tuple[str | None, str, str]:
    """Return (api_key_or_None, model, source).

    source is one of "learner", "global", "none". Learner decrypt failures
    fall through to the global key rather than crashing the request.
    """
    settings = get_settings()
    row = db.scalar(select(LearnerLLMKey).where(LearnerLLMKey.owner_id == owner_id))
    if row is not None and row.provider == PROVIDER_GROQ and (
        not row.model or row.model in settings.llm_allowed_models
    ):
        try:
            api_key = decrypt_key(row.encrypted_key)
        except ValidationError:
            api_key = None
        if api_key:
            model = row.model or settings.llm_model
            return api_key, model, "learner"
    route = (getattr(settings, "aria_llm_provider", None) or "groq").strip().lower()
    global_key = getattr(settings, "aria_llm_api_key", None) or (settings.groq_api_key if route == "groq" else None)
    if global_key:
        return global_key, settings.llm_model, "global"
    return None, settings.llm_model, "none"


def get_llm_provider_for_owner(db: Session, *, owner_id: UUID):
    """Owner-aware provider factory. None means deterministic fallback."""
    from app.ai.providers import LiteLLMGroqProvider

    api_key, model, source = resolve_credential(db, owner_id=owner_id)
    if not api_key:
        return None
    # Learner keys are Groq keys; the deployment's own key follows ARIA_LLM_PROVIDER.
    deployment = (getattr(get_settings(), "aria_llm_provider", None) or "groq").strip().lower()
    route = "groq" if source == "learner" else deployment
    return LiteLLMGroqProvider(api_key=api_key, model=model, owner_id=owner_id, db=db, route=route)
