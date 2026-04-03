from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "esim-gateway"
    app_env: str = "development"
    app_debug: bool = False
    app_log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://esim:esim_secret@localhost:5432/esim_gateway"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # eSIM Access provider — credentials from console.esimaccess.com
    esim_access_access_code: str = ""
    esim_access_secret_key: str = ""
    esim_access_base_url: str = "https://api.esimaccess.com"

    # Internal service auth (JSON array of client objects)
    internal_service_clients: str = "[]"

    # Idempotency
    idempotency_key_ttl_seconds: int = 86400

    # Provider client
    provider_request_timeout_seconds: int = 30
    provider_max_retries: int = 3

    # Background tasks
    catalog_sync_interval_seconds: int = 3600
    reconciliation_interval_seconds: int = 300

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url_str(self) -> str:
        return str(self.database_url)

    @property
    def redis_url_str(self) -> str:
        return str(self.redis_url)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
