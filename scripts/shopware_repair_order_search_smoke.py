"""Read-only live Shop-Ware repair order search smoke test.

Loads credentials from .env and performs only:

    GET /api/v1/tenants/{tenant_id}/repair_orders

Optionally set SHOPWARE_REPAIR_ORDER_SMOKE_CUSTOMER_ID,
SHOPWARE_REPAIR_ORDER_SMOKE_VEHICLE_ID, or SHOPWARE_REPAIR_ORDER_SMOKE_NUMBER.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, ExternalServiceNotConfiguredError
from app.integrations.shopware.adapter import ShopWareRepairOrderAdapter
from app.integrations.shopware.client import ShopWareClient


def _count(response: Any) -> int | None:
    if isinstance(response, dict) and isinstance(response.get("results"), list):
        return len(response["results"])
    return None


def _int_env(name: str) -> int | None:
    value = os.getenv(name)
    return int(value) if value else None


def main() -> int:
    settings = Settings()
    missing = [
        name
        for name, value in {
            "SHOPWARE_BASE_URL": settings.shopware_base_url,
            "SHOPWARE_API_PARTNER_ID": settings.shopware_api_partner_id,
            "SHOPWARE_API_SECRET": settings.shopware_api_secret,
            "SHOPWARE_TENANT_ID": settings.shopware_tenant_id,
        }.items()
        if not value
    ]
    if missing:
        print(f"Missing required Shop-Ware settings: {', '.join(missing)}", file=sys.stderr)
        return 2

    if settings.shopware_mode.lower() != "live":
        print("SHOPWARE_MODE is not live; running read-only live repair order search without changing app mode.")

    adapter = ShopWareRepairOrderAdapter(settings, ShopWareClient(settings))
    try:
        response = adapter.search(
            shop_id=settings.shopware_default_shop_id,
            customer_id=_int_env("SHOPWARE_REPAIR_ORDER_SMOKE_CUSTOMER_ID"),
            vehicle_id=_int_env("SHOPWARE_REPAIR_ORDER_SMOKE_VEHICLE_ID"),
            number=_int_env("SHOPWARE_REPAIR_ORDER_SMOKE_NUMBER"),
            page=1,
            per_page=5,
        )
    except (ExternalServiceError, ExternalServiceNotConfiguredError, ValueError) as exc:
        print(f"Shop-Ware repair order search smoke test failed: {exc}", file=sys.stderr)
        return 1

    print("Shop-Ware repair order search smoke test passed.")
    print(f"Read-only endpoint: GET /api/v1/tenants/{settings.shopware_tenant_id}/repair_orders")
    result_count = _count(response)
    if result_count is not None:
        print(f"Repair orders returned: {result_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
