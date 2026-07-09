from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Your New Mechanic Automation"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./ynm_automation.db"

    shopware_base_url: str | None = None
    shopware_mode: str = "mock"
    shopware_api_token: str | None = Field(default=None, repr=False)
    shopware_auth_header_name: str = "Authorization"
    shopware_auth_scheme: str = "Bearer"
    shopware_client_id: str | None = None
    shopware_client_secret: str | None = Field(default=None, repr=False)
    shopware_timeout_seconds: int = 15
    shopware_retry_attempts: int = 3
    shopware_retry_backoff_seconds: float = 0.5
    shopware_appointment_create_path: str | None = None
    shopware_appointment_update_path: str | None = None
    shopware_appointment_cancel_path: str | None = None
    shopware_customer_search_path: str | None = None
    shopware_vehicle_search_path: str | None = None
    shopware_repair_order_search_path: str | None = None
    shopware_appointment_id_field: str = "id"

    @property
    def shopware_configured(self) -> bool:
        return self.shopware_mode == "mock" or bool(
            self.shopware_base_url and (self.shopware_api_token or self.shopware_client_secret)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
