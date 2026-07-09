"""Read-only live Shop-Ware vehicle search smoke test.

Loads credentials from .env and performs only:

    GET /api/v1/tenants/{tenant_id}/vehicles

Optionally set SHOPWARE_VEHICLE_SMOKE_VIN or SHOPWARE_VEHICLE_SMOKE_CUSTOMER_ID.
The default VIN is intentionally unlikely to match a real vehicle.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, ExternalServiceNotConfiguredError
from app.integrations.shopware.adapter import ShopWareVehicleAdapter
from app.integrations.shopware.client import ShopWareClient


def _count(response: Any) -> int | None:
    if isinstance(response, dict) and isinstance(response.get("results"), list):
        return len(response["results"])
    return None


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
        print("SHOPWARE_MODE is not live; running read-only live vehicle search without changing app mode.")

    adapter = ShopWareVehicleAdapter(settings, ShopWareClient(settings))
    vin = os.getenv("SHOPWARE_VEHICLE_SMOKE_VIN", "YNM_SMOKE_TEST_NO_MATCH")
    customer_id = os.getenv("SHOPWARE_VEHICLE_SMOKE_CUSTOMER_ID")

    try:
        response = adapter.search(
            vin=vin if not customer_id else None,
            customer_id=int(customer_id) if customer_id else None,
            page=1,
            per_page=5,
        )
    except (ExternalServiceError, ExternalServiceNotConfiguredError, ValueError) as exc:
        print(f"Shop-Ware vehicle search smoke test failed: {exc}", file=sys.stderr)
        return 1

    print("Shop-Ware vehicle search smoke test passed.")
    print(f"Read-only endpoint: GET /api/v1/tenants/{settings.shopware_tenant_id}/vehicles")
    if customer_id:
        print(f"Customer ID filter: {customer_id}")
    else:
        print(f"VIN filter: {vin}")
    result_count = _count(response)
    if result_count is not None:
        print(f"Vehicles returned: {result_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
