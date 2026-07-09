import logging

import pytest

from app.core.config import Settings
from app.core.exceptions import ExternalServiceNotConfiguredError
from app.core.startup import validate_shopware_startup


def test_startup_allows_integration_test_mode_without_live_credentials(caplog):
    caplog.set_level(logging.INFO)
    settings = Settings(
        integration_test_mode=True,
        shopware_base_url=None,
        shopware_api_partner_id=None,
        shopware_api_secret=None,
        shopware_tenant_id=None,
        shopware_default_shop_id=None,
    )

    validate_shopware_startup(settings)

    records = [record for record in caplog.records if record.getMessage() == "Shop-Ware Mode Selected"]
    assert records
    assert records[0].shopware_mode == "mock"


def test_startup_rejects_live_mode_with_missing_shopware_config():
    settings = Settings(
        integration_test_mode=False,
        shopware_base_url="https://api.shop-ware.com",
        shopware_api_partner_id=None,
        shopware_api_secret=None,
        shopware_tenant_id=None,
        shopware_default_shop_id=None,
    )

    with pytest.raises(ExternalServiceNotConfiguredError) as exc:
        validate_shopware_startup(settings)

    message = str(exc.value)
    assert "Live Shop-Ware mode requires" in message
    assert "SHOPWARE_API_PARTNER_ID" in message
    assert "SHOPWARE_API_SECRET" in message
    assert "SHOPWARE_TENANT_ID" in message
    assert "SHOPWARE_DEFAULT_SHOP_ID" in message


def test_startup_accepts_live_mode_with_required_shopware_config(caplog):
    caplog.set_level(logging.INFO)
    settings = Settings(
        integration_test_mode=False,
        shopware_base_url="https://api.shop-ware.com",
        shopware_api_partner_id="partner-123",
        shopware_api_secret="secret-456",
        shopware_tenant_id=99,
        shopware_default_shop_id=7,
    )

    validate_shopware_startup(settings)

    enabled_records = [record for record in caplog.records if record.getMessage() == "Live Shop-Ware mode enabled"]
    assert enabled_records
    assert enabled_records[0].tenant_id == 99
    assert enabled_records[0].default_shop_id == 7
    for record in caplog.records:
        assert "secret-456" not in record.getMessage()
