import ast
import re
from pathlib import Path

from app.core.config import Settings


def test_model_defaults_match_across_supported_configs():
    expected = Settings.model_fields["aria_llm_allowed_models"].default
    for filename in ("docker-compose.yml", "docker-compose.prod.yml"):
        source = Path(filename).read_text(encoding="utf-8")
        match = re.search(r"ARIA_LLM_ALLOWED_MODELS: \$\{ARIA_LLM_ALLOWED_MODELS:-(.*?)\}", source)
        assert match and match.group(1) == expected
    sample = Path(".env.example").read_text(encoding="utf-8")
    assert f"ARIA_LLM_ALLOWED_MODELS={expected}" in sample
    tree = ast.parse(Path("scripts/check_prod_secrets.py").read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.Constant) and node.value == expected for node in ast.walk(tree))


def test_development_forwards_optional_capabilities_and_keeps_storage():
    source = Path("docker-compose.yml").read_text(encoding="utf-8")
    for key in ("ARIA_LLM_KEYS_ENCRYPTION_KEY", "ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD",
                "ARIA_TTS_API_KEY", "ARIA_STT_API_KEY", "ARIA_EMBEDDING_API_KEY",
                "SMTP_HOST", "SMTP_PASSWORD", "ARIA_VAPID_PRIVATE_KEY"):
        assert f"{key}: ${{{key}:-}}" in source
    assert "audio-data:/app/audiofiles" in source
    assert "ARIA_BACKUP_ENABLED:-false" in source
    assert "condition: service_completed_successfully" in source
    assert "command: alembic upgrade head" in source
    dockerfile = Path("backend/Dockerfile").read_text(encoding="utf-8")
    assert "COPY database /app/database" in dockerfile
    assert "COPY alembic.ini /app/alembic.ini" in dockerfile


def test_container_tools_match_supported_runtime_features():
    for filename in ("backend/Dockerfile", "backend/Dockerfile.prod"):
        source = Path(filename).read_text(encoding="utf-8")
        assert "FROM python:3.12-slim-trixie" in source
        assert "ca-certificates espeak-ng" in source
        assert "postgresql-client-16" in source
        assert "trixie-pgdg main" in source
        assert "signed-by=" in source
