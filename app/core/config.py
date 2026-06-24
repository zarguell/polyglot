from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # App
    app_name: str = "Polyglot"
    environment: Literal["local", "dev", "staging", "production"] = "local"
    secret_key: SecretStr = SecretStr("CHANGE-ME-32-CHARACTERS-LONG-MINIMUM")
    enable_openapi: bool = True
    enable_alpine: bool = False

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://polyglot:polyglot@localhost:5432/polyglot",
        validation_alias="DATABASE_URL",
    )

    # Auth
    auth_dev_mode: bool = False
    auth_oidc_provider: Literal["generic", "entra", "okta", "google"] = "generic"
    auth_oidc_client_id: str | None = None
    auth_oidc_client_secret: SecretStr | None = None
    auth_oidc_discovery_url: AnyHttpUrl | None = None
    auth_oidc_tenant: str | None = None
    auth_oidc_domain: str | None = None
    # Auth — SAML
    auth_saml_enabled: bool = False
    auth_saml_idp_metadata_url: str | None = None
    auth_saml_sp_entity_id: str = "polyglot"
    auth_saml_sp_private_key: SecretStr | None = None
    auth_saml_sp_cert: SecretStr | None = None

    session_max_age_seconds: int = 43200  # 12 hours

    # Security
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    cors_allowed_origins: list[str] = []

    # Components (comma-separated in .env, e.g. "webhooks,smtp,totp_mfa")
    installed_components: list[str] | None = None

    # SMTP (used by the smtp component)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = True
    email_from: str = ""

    # Redis Cache (used by the redis_cache component)
    redis_url: str = "redis://redis:6379/0"

    # Stripe (used by the stripe component)
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_id: str = ""

    # File Storage (used by the file_storage component)
    storage_backend: str = "local"
    storage_local_path: str = "./storage"
    aws_bucket: str = ""
    aws_region: str = "us-east-1"

    @field_validator("installed_components", mode="before")
    @classmethod
    def _parse_installed_components(cls, v: str | list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return [s.strip() for s in v if s.strip()]
        if isinstance(v, str):
            items = [s.strip() for s in v.split(",") if s.strip()]
            return items if items else None
        return None

    # Tasks
    procrastinate_schema: str = "procrastinate"

    def check_sanity(self) -> None:
        """Raise ValueError on unsafe config combinations."""
        if self.environment == "production" and self.auth_dev_mode:
            msg = "AUTH_DEV_MODE is forbidden when ENVIRONMENT=production"
            raise ValueError(msg)
        if self.environment != "local" and len(self.secret_key.get_secret_value()) < 32:
            msg = "SECRET_KEY must be at least 32 characters in non-local environments"
            raise ValueError(msg)
        if self.environment != "local":
            self.enable_openapi = False


settings = Settings()  # type: ignore[call-arg]
settings.check_sanity()
