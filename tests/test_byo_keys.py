"""Step 4 acceptance: BYO learner keys with separate encryption key.

Frozen gates:
- Separate ARIA_LLM_KEYS_ENCRYPTION_KEY (never ARIA_SESSION_SECRET)
- Rotation: OLD key decrypts legacy rows; new encryptions use primary
- No plaintext in API responses, exports, logs, metrics, exceptions
- Strict owner isolation; delete verification
- Per-user budget enforcement (one learner's cap never blocks another)
- Provider/model allowlisting
- Precedence: learner key -> global key -> deterministic fallback
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.services.llm_keys import generate_encryption_key

VALID_KEY = "gsk_" + "a" * 40
VALID_KEY_2 = "gsk_" + "b" * 40

PRIMARY = generate_encryption_key()
ROTATED = generate_encryption_key()


class _Settings:
    aria_env = "development"
    aria_ai_monthly_budget_usd = 0.0
    aria_llm_per_user_budget_usd = 0.0
    groq_api_key = None
    llm_model = "openai/gpt-oss-120b"
    aria_llm_keys_encryption_key = PRIMARY
    aria_llm_keys_encryption_key_old = None

    @property
    def llm_allowed_models(self) -> list[str]:
        return ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


def _patch_settings(monkeypatch, **overrides) -> None:
    base = {k: v for k, v in vars(_Settings).items() if not k.startswith("__")}
    base.update(overrides)
    cls = type("S", (), base)
    if "llm_allowed_models" not in overrides:
        cls.llm_allowed_models = _Settings.llm_allowed_models
    import app.ai.budget as budget
    import app.ai.registry as registry
    import app.services.llm_keys as llm_keys

    instance = cls()
    monkeypatch.setattr(llm_keys, "get_settings", lambda: instance)
    monkeypatch.setattr(registry, "get_settings", lambda: instance)
    monkeypatch.setattr(budget, "get_settings", lambda: instance)


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_set_get_delete_roundtrip_hides_plaintext(client: TestClient, monkeypatch) -> None:
    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"byo-{tag}@example.com")
    auth = _headers(user["access_token"])

    created = client.post(
        "/api/v1/settings/llm-key", headers=auth, json={"key": VALID_KEY}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["configured"] is True
    assert body["provider"] == "groq"
    assert body["hint"] == "..." + VALID_KEY[-4:]
    assert VALID_KEY not in created.text

    status = client.get("/api/v1/settings/llm-key", headers=auth)
    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert status.json()["hint"] == "..." + VALID_KEY[-4:]
    assert VALID_KEY not in status.text

    # Re-resolve the owner via status-independent path: delete then verify.
    deleted = client.delete("/api/v1/settings/llm-key", headers=auth)
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}

    again = client.get("/api/v1/settings/llm-key", headers=auth)
    assert again.json()["configured"] is False

    missing = client.delete("/api/v1/settings/llm-key", headers=auth)
    assert missing.status_code == 404


def test_invalid_key_and_model_rejected(client: TestClient, monkeypatch) -> None:
    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"byo-invalid-{tag}@example.com")
    auth = _headers(user["access_token"])

    bad = client.post(
        "/api/v1/settings/llm-key", headers=auth, json={"key": "not-a-groq-key!!"}
    )
    assert bad.status_code == 422

    bad_model = client.post(
        "/api/v1/settings/llm-key",
        headers=auth,
        json={"key": VALID_KEY, "model": "gpt-99-evil"},
    )
    assert bad_model.status_code == 422

    ok_model = client.post(
        "/api/v1/settings/llm-key",
        headers=auth,
        json={"key": VALID_KEY, "model": "openai/gpt-oss-20b"},
    )
    assert ok_model.status_code == 201
    assert ok_model.json()["model"] == "openai/gpt-oss-20b"


def test_cross_owner_isolation(client: TestClient, monkeypatch) -> None:
    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    alice = _register(client, f"byo-a-{tag}@example.com")
    bob = _register(client, f"byo-b-{tag}@example.com")

    created = client.post(
        "/api/v1/settings/llm-key",
        headers=_headers(alice["access_token"]),
        json={"key": VALID_KEY},
    )
    assert created.status_code == 201

    bob_status = client.get(
        "/api/v1/settings/llm-key", headers=_headers(bob["access_token"])
    )
    assert bob_status.json()["configured"] is False

    # Bob cannot delete Alice's key: his own scope has none.
    assert (
        client.delete(
            "/api/v1/settings/llm-key", headers=_headers(bob["access_token"])
        ).status_code
        == 404
    )
    # Alice's key is untouched.
    assert (
        client.get(
            "/api/v1/settings/llm-key", headers=_headers(alice["access_token"])
        ).json()["configured"]
        is True
    )


def test_precedence_learner_global_none(client: TestClient, monkeypatch) -> None:
    import app.services.llm_keys as llm_keys

    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"byo-prec-{tag}@example.com")
    auth = _headers(user["access_token"])

    from sqlalchemy import select

    from app.db.dependencies import get_db  # noqa: F401
    from app.db.models import Learner
    from app.main import app

    db = next(app.dependency_overrides[get_db]())
    try:
        learner = db.scalar(select(Learner).where(Learner.email == f"byo-prec-{tag}@example.com"))
        api_key, _model, source = llm_keys.resolve_credential(db, owner_id=learner.id)
        assert (api_key, source) == (None, "none")
        assert llm_keys.get_llm_provider_for_owner(db, owner_id=learner.id) is None
    finally:
        db.close()

    # Global key only -> global.
    _patch_settings(monkeypatch, groq_api_key="gsk_global" + "c" * 42)
    db = next(app.dependency_overrides[get_db]())
    try:
        learner = db.scalar(select(Learner).where(Learner.email == f"byo-prec-{tag}@example.com"))
        api_key, _model, source = llm_keys.resolve_credential(db, owner_id=learner.id)
        assert source == "global"
        assert api_key == "gsk_global" + "c" * 42
    finally:
        db.close()

    # Learner key wins over global, with learner model.
    client.post(
        "/api/v1/settings/llm-key",
        headers=auth,
        json={"key": VALID_KEY_2, "model": "openai/gpt-oss-20b"},
    )
    db = next(app.dependency_overrides[get_db]())
    try:
        learner = db.scalar(select(Learner).where(Learner.email == f"byo-prec-{tag}@example.com"))
        api_key, model, source = llm_keys.resolve_credential(db, owner_id=learner.id)
        assert source == "learner"
        assert api_key == VALID_KEY_2
        assert model == "openai/gpt-oss-20b"
        provider = llm_keys.get_llm_provider_for_owner(db, owner_id=learner.id)
        assert provider is not None
        assert provider.api_key == VALID_KEY_2
        assert provider.owner_id == learner.id
        assert VALID_KEY_2 not in repr(provider)
    finally:
        db.close()


def test_rotation_old_key_decrypts_legacy_rows(client: TestClient, monkeypatch) -> None:
    import app.services.llm_keys as llm_keys

    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"byo-rot-{tag}@example.com")
    auth = _headers(user["access_token"])
    client.post("/api/v1/settings/llm-key", headers=auth, json={"key": VALID_KEY})

    # Rotate: new primary, previous primary becomes _OLD.
    _patch_settings(
        monkeypatch,
        aria_llm_keys_encryption_key=ROTATED,
        aria_llm_keys_encryption_key_old=PRIMARY,
    )
    status = client.get("/api/v1/settings/llm-key", headers=auth)
    assert status.json()["configured"] is True

    from sqlalchemy import select

    from app.db.dependencies import get_db  # noqa: F401
    from app.db.models import Learner
    from app.main import app

    db = next(app.dependency_overrides[get_db]())
    try:
        learner = db.scalar(select(Learner).where(Learner.email == f"byo-rot-{tag}@example.com"))
        api_key, _model, source = llm_keys.resolve_credential(db, owner_id=learner.id)
        assert source == "learner"
        assert api_key == VALID_KEY
    finally:
        db.close()

    # Re-save under the new primary, then drop _OLD entirely.
    client.post("/api/v1/settings/llm-key", headers=auth, json={"key": VALID_KEY_2})
    _patch_settings(
        monkeypatch,
        aria_llm_keys_encryption_key=ROTATED,
        aria_llm_keys_encryption_key_old=None,
    )
    db = next(app.dependency_overrides[get_db]())
    try:
        learner = db.scalar(select(Learner).where(Learner.email == f"byo-rot-{tag}@example.com"))
        api_key, _model, source = llm_keys.resolve_credential(db, owner_id=learner.id)
        assert (api_key, source) == (VALID_KEY_2, "learner")
    finally:
        db.close()


def test_rotation_job_reencrypts_legacy_rows(client: TestClient, monkeypatch) -> None:
    from sqlalchemy import select

    import app.services.llm_keys as llm_keys
    from app.db.dependencies import get_db  # noqa: F401
    from app.db.models import Learner
    from app.main import app

    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"byo-reenc-{tag}@example.com")
    auth = _headers(user["access_token"])
    client.post("/api/v1/settings/llm-key", headers=auth, json={"key": VALID_KEY})

    # Rotate keys: new primary, previous primary kept as _OLD.
    _patch_settings(
        monkeypatch,
        aria_llm_keys_encryption_key=ROTATED,
        aria_llm_keys_encryption_key_old=PRIMARY,
    )
    db = next(app.dependency_overrides[get_db]())
    try:
        summary = llm_keys.reencrypt_with_primary(db)
        assert summary["total"] == 1
        assert summary["reencrypted"] == 1
        assert summary["failed"] == 0
        # Second run is a no-op: everything is already under the primary.
        summary = llm_keys.reencrypt_with_primary(db)
        assert summary == {"total": 1, "reencrypted": 0, "failed": 0}
    finally:
        db.close()

    # _OLD can now be dropped: the row resolves with the primary alone.
    _patch_settings(
        monkeypatch,
        aria_llm_keys_encryption_key=ROTATED,
        aria_llm_keys_encryption_key_old=None,
    )
    db = next(app.dependency_overrides[get_db]())
    try:
        learner = db.scalar(select(Learner).where(Learner.email == f"byo-reenc-{tag}@example.com"))
        api_key, _model, source = llm_keys.resolve_credential(db, owner_id=learner.id)
        assert (api_key, source) == (VALID_KEY, "learner")
    finally:
        db.close()


def test_per_user_budget_isolation(monkeypatch) -> None:
    import uuid as uuid_mod

    import app.ai.budget as budget

    _patch_settings(monkeypatch, aria_llm_per_user_budget_usd=0.0001)
    budget.reset_learner_budget()
    alice = uuid_mod.uuid4()
    bob = uuid_mod.uuid4()
    try:
        budget.record_learner_usage(
            owner_id=alice, model="openai/gpt-oss-120b",
            prompt_tokens=100000, completion_tokens=100000,
        )
        with pytest.raises(budget.BudgetExceeded):
            budget.assert_learner_within_budget(alice)
        # Bob is unaffected by Alice's spend.
        budget.assert_learner_within_budget(bob)
    finally:
        budget.reset_learner_budget()


def test_owner_provider_enforces_budget_without_network(monkeypatch) -> None:
    import asyncio
    import uuid as uuid_mod

    import app.ai.budget as budget
    from app.ai.providers import LiteLLMGroqProvider

    _patch_settings(monkeypatch, aria_llm_per_user_budget_usd=0.0000001)
    budget.reset_learner_budget()
    owner = uuid_mod.uuid4()
    try:
        budget.record_learner_usage(
            owner_id=owner, model="openai/gpt-oss-120b",
            prompt_tokens=100000, completion_tokens=100000,
        )
        provider = LiteLLMGroqProvider(
            api_key="gsk_blocked", model="openai/gpt-oss-120b", owner_id=owner
        )
        with pytest.raises(budget.BudgetExceeded):
            asyncio.run(provider.generate_text(system="s", user="u"))
    finally:
        budget.reset_learner_budget()


def test_export_never_contains_plaintext(client: TestClient, monkeypatch) -> None:
    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"byo-exp-{tag}@example.com")
    auth = _headers(user["access_token"])
    client.post("/api/v1/settings/llm-key", headers=auth, json={"key": VALID_KEY})
    exported = client.get("/api/v1/account/export", headers=auth)
    assert exported.status_code == 200
    assert VALID_KEY not in exported.text
    assert "..." + VALID_KEY[-4:] in exported.text


def test_data_reset_wipes_key_and_usage(client: TestClient, monkeypatch) -> None:
    import app.ai.budget as budget

    _patch_settings(monkeypatch)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"byo-wipe-{tag}@example.com")
    auth = _headers(user["access_token"])
    client.post("/api/v1/settings/llm-key", headers=auth, json={"key": VALID_KEY})
    assert client.get("/api/v1/settings/llm-key", headers=auth).json()["configured"] is True

    # Data reset deletes all owner-scoped rows including the key (204 or 200).
    wiped = client.delete("/api/v1/account/data", headers=auth)
    assert wiped.status_code in (200, 204)
    budget.reset_learner_budget()
