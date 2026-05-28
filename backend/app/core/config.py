"""Application configuration via Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings, loaded from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://ratiba:dev_password@db:5432/ratiba",
        alias="DATABASE_URL",
    )
    test_database_url: str = Field(
        default="postgresql+psycopg://ratiba:dev_password@db:5432/ratiba_test",
        alias="TEST_DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # Anthropic
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model_parser: str = Field(default="claude-sonnet-4-5", alias="ANTHROPIC_MODEL_PARSER")
    anthropic_model_conversational: str = Field(
        default="claude-haiku-4-5", alias="ANTHROPIC_MODEL_CONVERSATIONAL"
    )

    # Telegram
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str = Field(default="", alias="TELEGRAM_WEBHOOK_URL")

    # Security
    secret_key: str = Field(
        default="change_me_dev_only_change_me_dev_only_change_me_dev_only_12345",
        alias="SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(default=30, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # Compliance
    kdpa_data_region: str = Field(default="ke-1", alias="KDPA_DATA_REGION")
    kdpa_registration_ref: str = Field(default="", alias="KDPA_REGISTRATION_REF")

    # Observability
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    # URLs
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")

    # Audit pack storage (Phase 5 — local FS; Phase 6 — S3 if bucket set)
    audit_pack_dir: str = Field(default="/app/audit_packs", alias="AUDIT_PACK_DIR")
    audit_pack_s3_bucket: str = Field(default="", alias="AUDIT_PACK_S3_BUCKET")
    audit_pack_s3_endpoint: str = Field(default="", alias="AUDIT_PACK_S3_ENDPOINT")
    audit_pack_s3_region: str = Field(default="", alias="AUDIT_PACK_S3_REGION")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — call this everywhere instead of instantiating."""
    return Settings()
