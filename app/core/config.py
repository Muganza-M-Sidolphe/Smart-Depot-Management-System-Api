from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    upload_dir: str = Field(default="uploads", validation_alias="UPLOAD_DIR")
    public_base_url: str = Field(
        default="http://127.0.0.1:8000",
        validation_alias="PUBLIC_BASE_URL",
    )
    # Frontend base URL used to build the login link in emails.
    frontend_url: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")

    # Email / SMTP. When smtp_host is empty, emails are logged instead of sent
    # (handy for local development without real mail credentials).
    smtp_host: str = Field(default="", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")
    email_from: str = Field(default="no-reply@smartdepot.local", validation_alias="EMAIL_FROM")
    email_from_name: str = Field(default="Smart Depot", validation_alias="EMAIL_FROM_NAME")

    # Automatic report scheduler (APScheduler, in-process)
    enable_scheduler: bool = Field(default=True, validation_alias="ENABLE_SCHEDULER")
    # IANA timezone used for report scheduling (send_hour) and display labels.
    timezone: str = Field(default="Africa/Kigali", validation_alias="TIMEZONE")

    def tzinfo(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            return ZoneInfo("UTC")

    @property
    def emails_enabled(self) -> bool:
        return bool(self.smtp_host)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
