from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Your New Mechanic Automation"
    app_env: str = "local"
    app_local_timezone: str = "America/New_York"
    log_level: str = "INFO"
    log_format: str = "text"
    integration_test_mode: bool = False
    idempotency_ttl_seconds: int = 86400
    database_url: str = "sqlite:///./ynm_automation.db"

    shopware_base_url: str | None = None
    shopware_mode: str = "live"
    shopware_api_partner_id: str | None = Field(default=None, repr=False)
    shopware_api_secret: str | None = Field(default=None, repr=False)
    shopware_tenant_id: int | None = None
    shopware_default_shop_id: int | None = None
    shopware_default_staff_id: int | None = None
    shopware_api_token: str | None = Field(default=None, repr=False)
    shopware_auth_header_name: str = "Authorization"
    shopware_auth_scheme: str = "Bearer"
    shopware_client_id: str | None = None
    shopware_client_secret: str | None = Field(default=None, repr=False)
    shopware_timeout_seconds: int = 15
    shopware_retry_attempts: int = 3
    shopware_retry_backoff_seconds: float = 0.5
    shopware_appointment_create_path: str = "/api/v1/tenants/{tenant_id}/appointments"
    shopware_appointment_update_path: str = "/api/v1/tenants/{tenant_id}/appointments/{appointment_id}"
    shopware_appointment_cancel_path: str = "/api/v1/tenants/{tenant_id}/appointments/{appointment_id}"
    shopware_customer_search_path: str = "/api/v1/tenants/{tenant_id}/customers"
    shopware_customer_create_path: str = "/api/v1/tenants/{tenant_id}/customers"
    shopware_customer_detail_path: str = "/api/v1/tenants/{tenant_id}/customers/{customer_id}"
    shopware_vehicle_search_path: str = "/api/v1/tenants/{tenant_id}/vehicles"
    shopware_vehicle_create_path: str = "/api/v1/tenants/{tenant_id}/vehicles"
    shopware_vehicle_detail_path: str = "/api/v1/tenants/{tenant_id}/vehicles/{vehicle_id}"
    shopware_repair_order_search_path: str = "/api/v1/tenants/{tenant_id}/repair_orders"
    shopware_repair_order_create_path: str = "/api/v1/tenants/{tenant_id}/repair_orders"
    shopware_repair_order_detail_path: str = "/api/v1/tenants/{tenant_id}/repair_orders/{repair_order_id}"
    shopware_appointment_id_field: str = "id"

    @property
    def shopware_configured(self) -> bool:
        return self.shopware_mode_name == "mock" or not self.missing_shopware_live_settings()

    @property
    def shopware_mode_name(self) -> str:
        return "mock" if self.integration_test_mode else "live"

    def missing_shopware_live_settings(self) -> list[str]:
        required = {
            "SHOPWARE_BASE_URL": self.shopware_base_url,
            "SHOPWARE_API_PARTNER_ID": self.shopware_api_partner_id,
            "SHOPWARE_API_SECRET": self.shopware_api_secret,
            "SHOPWARE_TENANT_ID": self.shopware_tenant_id,
            "SHOPWARE_DEFAULT_SHOP_ID": self.shopware_default_shop_id,
        }
        return [name for name, value in required.items() if not value]

    @field_validator(
        "shopware_api_partner_id",
        "shopware_api_secret",
        "shopware_tenant_id",
        "shopware_default_shop_id",
        "shopware_default_staff_id",
        "shopware_client_id",
        "shopware_client_secret",
        mode="before",
    )
    @classmethod
    def blank_env_values_are_none(cls, value):
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
