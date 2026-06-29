from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(
        default="Smart Depot Management System API",
        validation_alias="APP_NAME",
    )
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    database_url: str = Field(default="sqlite:///./smart_depot.db", validation_alias="DATABASE_URL")
    backend_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias="BACKEND_CORS_ORIGINS",
    )
    secret_key: str = Field(
        default="change-me-in-production-please-set-a-long-random-secret",
        validation_alias="SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60 * 24,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
