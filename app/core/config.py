from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, SecretStr
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
    session_max_age_seconds: int = 43200  # 12 hours

    # Security
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    cors_allowed_origins: list[str] = []

    # Components
    installed_components: list[str] | None = None

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
