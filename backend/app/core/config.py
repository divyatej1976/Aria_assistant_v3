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
    groq_api_key: str | None = Field(default=None, repr=False)
    llm_model: str = "llama-3.3-70b-versatile"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.aria_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
