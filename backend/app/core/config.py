from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aria_env: str = "development"
    aria_log_level: str = "INFO"
    aria_api_prefix: str = "/api/v1"
    aria_cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://aria:aria@localhost:5432/aria"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_jwt_secret: str | None = Field(default=None, repr=False)
    aria_session_secret: str | None = Field(default=None, repr=False)
    groq_api_key: str | None = Field(default=None, repr=False)
    llm_model: str = "llama-3.3-70b-versatile"
    aria_trusted_hosts: str = "localhost,127.0.0.1"
    aria_rate_limit_enabled: bool = True
    aria_rate_limit_requests: int = 10
    aria_rate_limit_window_seconds: int = 60
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
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = Field(default=None, repr=False)
    smtp_from: str = "ARIA <noreply@aria.local>"
    smtp_use_tls: bool = True
    aria_tts_provider: str = "auto"  # auto | cloud | local
    aria_tts_api_key: str | None = Field(default=None, repr=False)
    aria_stt_api_key: str | None = Field(default=None, repr=False)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.aria_cors_origins.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.aria_trusted_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
