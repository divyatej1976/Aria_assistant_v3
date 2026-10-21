from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Hosts (Render, Heroku) hand out postgres(ql):// URLs; SQLAlchemy would pick the
    uninstalled psycopg2 for those, so point them at the psycopg 3 driver we ship."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    # keys.env (optional, private) is read after .env, so the AI keys put there win.
    model_config = SettingsConfigDict(env_file=(".env", "keys.env"), extra="ignore")

    aria_env: str = "development"
    aria_log_level: str = "INFO"
    aria_cors_origins: str = "http://localhost:3000"
    aria_public_url: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://aria:aria@localhost:5432/aria"
    # legacy/inactive: Supabase auth was never wired; session cookies are the active scheme
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_jwt_secret: str | None = Field(default=None, repr=False)
    aria_session_secret: str | None = Field(default=None, repr=False)
    groq_api_key: str | None = Field(default=None, repr=False)
    llm_model: str = "openai/gpt-oss-120b"
    # The app's own AI provider: "groq" (default), "openai" or "gemini". With openai/gemini set
    # ARIA_LLM_API_KEY and an LLM_MODEL from that provider, e.g. gpt-4o-mini or gemini-2.5-flash.
    aria_llm_provider: str = "groq"
    aria_llm_api_key: str | None = Field(default=None, repr=False)
    aria_brain_routing: bool = False
    aria_brain_llm_routing: bool = False
    aria_brain_checkpoint_path: str = "aria-brain-checkpoints.db"
    # Per-learner BYO keys (Step 4): separate Fernet key, NEVER the session secret.
    # Rotating ARIA_SESSION_SECRET must not invalidate encrypted learner keys.
    # Rotation: set _OLD to the previous primary, re-encrypt, then drop _OLD.
    aria_llm_keys_encryption_key: str | None = Field(default=None, repr=False)
    aria_llm_keys_encryption_key_old: str | None = Field(default=None, repr=False)
    aria_llm_allowed_models: str = (
        "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b,"
        "llama-3.3-70b-versatile,llama-3.1-8b-instant"
    )
    # Per-learner monthly cap in USD (0 = unlimited). Global budget stays separate.
    aria_llm_per_user_budget_usd: float = 0.0
    # Completion-token limit reserved and passed to the provider when a
    # per-user budget is active. Admission/input estimates remain best-effort.
    aria_llm_completion_reserve_tokens: int = 512
    # Scheduled database backups (pg_dump). Only meaningful on PostgreSQL.
    aria_backup_enabled: bool = False
    aria_backup_dir: str = "backups"
    aria_backup_interval_hours: int = 24
    aria_backup_keep: int = 14
    # At-rest encryption for pg_dump archives (Fernet; dedicated key, never
    # the session secret). Unset = plaintext dumps (dev only).
    aria_backup_encryption_key: str | None = Field(default=None, repr=False)
    aria_embedding_api_key: str | None = Field(default=None, repr=False)
    aria_embedding_model: str = "text-embedding-3-small"
    aria_embedding_base_url: str | None = None
    aria_embedding_dim: int = 768
    aria_trusted_hosts: str = "localhost,127.0.0.1"
    aria_rate_limit_enabled: bool = True
    aria_rate_limit_requests: int = 10
    aria_rate_limit_window_seconds: int = 60
    # memory = per-process (single replica); db = shared fixed-window table
    # safe for multiple replicas (adds one upsert per limited request).
    aria_rate_limit_backend: str = "memory"  # memory | db
    aria_scheduler_enabled: bool = True
    aria_reminder_check_interval_minutes: int = 60
    aria_audio_queue_interval_seconds: int = 30
    aria_vapid_public_key: str | None = None
    aria_vapid_private_key: str | None = Field(default=None, repr=False)
    aria_vapid_subject: str = "mailto:noreply@aria.local"
    # Only browser push services may receive server-side notification requests.
    aria_push_allowed_hosts: str = (
        "fcm.googleapis.com,updates.push.services.mozilla.com,"
        "*.notify.windows.com,web.push.apple.com"
    )
    aria_sentry_dsn: str | None = Field(default=None, repr=False)
    aria_metrics_token: str | None = Field(default=None, repr=False)
    aria_langfuse_public_key: str | None = None
    aria_langfuse_secret_key: str | None = Field(default=None, repr=False)
    aria_langfuse_host: str | None = None
    aria_ai_monthly_budget_usd: float = 0.0
    aria_idempotency_ttl_seconds: int = Field(default=3600, gt=0)
    # Standalone sweeper interval for expired idempotency keys (scheduler job,
    # advisory-locked). Keeps the table clean even when no new inserts occur.
    aria_idempotency_sweep_interval_seconds: int = Field(default=600, gt=0)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = Field(default=None, repr=False)
    smtp_from: str = "ARIA <noreply@aria.local>"
    smtp_use_tls: bool = True
    aria_tts_provider: str = "auto"  # auto | cloud | local
    aria_tts_api_key: str | None = Field(default=None, repr=False)
    aria_stt_api_key: str | None = Field(default=None, repr=False)
    # Cloud audio via Groq rides on GROQ_API_KEY (no separate key needed).
    # The orpheus TTS model requires one-time terms acceptance by the Groq
    # org admin; until then the provider chain falls back automatically.
    aria_tts_model: str = "canopylabs/orpheus-v1-english"
    # Groq Orpheus English voices: autumn, diana, hannah, austin, daniel, troy.
    aria_tts_voice: str = "hannah"
    # The learner's voice in two-person episodes.
    aria_tts_voice_2: str = "troy"
    aria_stt_model: str = "whisper-large-v3"
    # Audio byte storage root (local dir; prod mounts a volume here).
    # S3-compatible backends implement AudioStorage later without migration:
    # artifacts carry a storage_key either way.
    aria_audio_dir: str = "audiofiles"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.aria_cors_origins.split(",") if origin.strip()]

    @property
    def llm_allowed_models(self) -> list[str]:
        return [
            model.strip()
            for model in self.aria_llm_allowed_models.split(",")
            if model.strip()
        ]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.aria_trusted_hosts.split(",") if host.strip()]

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3(cls, value: str) -> str:
        return normalize_database_url(value)

    @model_validator(mode="after")
    def _enforce_prod_database(self):
        """Prod runs on the bundled PostgreSQL only. SQLite is a dev/test
        fallback (pgvector→JSON, no pg_dump); refuse to boot it in prod."""
        if self.aria_env == "production" and self.database_url.startswith("sqlite"):
            raise ValueError(
                "ARIA_ENV=production requires a PostgreSQL DATABASE_URL "
                "(SQLite is dev/test only)"
            )
        if self.aria_env == "production":
            secret = self.aria_session_secret or self.supabase_jwt_secret
            if not secret or len(secret) < 32 or secret == "development-only-change-me":
                raise ValueError("Production requires a dedicated session secret of at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
