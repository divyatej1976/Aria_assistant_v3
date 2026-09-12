from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aria_env: str = "development"
    aria_log_level: str = "INFO"
    aria_api_prefix: str = "/api/v1"
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
    # Per-learner BYO keys (Step 4): separate Fernet key, NEVER the session secret.
    # Rotating ARIA_SESSION_SECRET must not invalidate encrypted learner keys.
    # Rotation: set _OLD to the previous primary, re-encrypt, then drop _OLD.
    aria_llm_keys_encryption_key: str | None = Field(default=None, repr=False)
    aria_llm_keys_encryption_key_old: str | None = Field(default=None, repr=False)
    aria_llm_allowed_models: str = "openai/gpt-oss-120b,openai/gpt-oss-20b"
    # Per-learner monthly cap in USD (0 = unlimited). Global budget stays separate.
    aria_llm_per_user_budget_usd: float = 0.0
    # Completion-token floor reserved per owner-scoped call when a per-user
    # budget is active; the concurrent overshoot bound is actual completion
    # tokens minus this floor. Raise it for tighter caps.
    aria_llm_completion_reserve_tokens: int = 512
    # Scheduled database backups (pg_dump). Only meaningful on PostgreSQL.
    aria_backup_enabled: bool = False
    aria_backup_dir: str = "backups"
    aria_backup_interval_hours: int = 24
    aria_backup_keep: int = 14
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
    aria_sentry_dsn: str | None = Field(default=None, repr=False)
    aria_langfuse_public_key: str | None = None
    aria_langfuse_secret_key: str | None = Field(default=None, repr=False)
    aria_langfuse_host: str | None = None
    aria_ai_monthly_budget_usd: float = 0.0
    aria_idempotency_ttl_seconds: int = 3600
    # Standalone sweeper interval for expired idempotency keys (scheduler job,
    # advisory-locked). Keeps the table clean even when no new inserts occur.
    aria_idempotency_sweep_interval_seconds: int = 600
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
    aria_tts_voice: str = "tara"
    aria_stt_model: str = "whisper-large-v3"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
