from app.core.config import Settings
from app.core.exceptions import ExternalServiceNotConfiguredError
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_shopware_startup(settings: Settings) -> None:
    mode = settings.shopware_mode_name
    logger.info(
        "Shop-Ware Mode Selected",
        extra={
            "shopware_mode": mode,
            "integration_test_mode": settings.integration_test_mode,
            "tenant_configured": settings.shopware_tenant_id is not None,
            "default_shop_configured": settings.shopware_default_shop_id is not None,
        },
    )

    if settings.integration_test_mode:
        logger.info("Shop-Ware mock/test-safe mode enabled")
        return

    missing = settings.missing_shopware_live_settings()
    if missing:
        raise ExternalServiceNotConfiguredError(
            "Live Shop-Ware mode requires these environment variables: " + ", ".join(missing)
        )

    logger.info(
        "Live Shop-Ware mode enabled",
        extra={
            "base_url": settings.shopware_base_url,
            "tenant_id": settings.shopware_tenant_id,
            "default_shop_id": settings.shopware_default_shop_id,
        },
    )
