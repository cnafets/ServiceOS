"""Read-only live Shop-Ware connectivity smoke test.

This script loads credentials from .env and performs only a documented GET
request against the official Shop-Ware API.
"""

from __future__ import annotations

import sys
from typing import Any

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, ExternalServiceNotConfiguredError
from app.integrations.shopware.client import ShopWareClient


def _tenant_count(response: Any) -> int | None:
    if isinstance(response, list):
        return len(response)
    if isinstance(response, dict) and isinstance(response.get("results"), list):
        return len(response["results"])
    return None


def _configured_tenant_seen(response: Any, tenant_id: int | None) -> bool | None:
    if tenant_id is None:
        return None
    tenants = response if isinstance(response, list) else response.get("results") if isinstance(response, dict) else None
    if not isinstance(tenants, list):
        return None
    return any(isinstance(tenant, dict) and tenant.get("id") == tenant_id for tenant in tenants)


def main() -> int:
    settings = Settings()

    missing = [
        name
        for name, value in {
            "SHOPWARE_BASE_URL": settings.shopware_base_url,
            "SHOPWARE_API_PARTNER_ID": settings.shopware_api_partner_id,
            "SHOPWARE_API_SECRET": settings.shopware_api_secret,
        }.items()
        if not value
    ]
    if missing:
        print(f"Missing required Shop-Ware settings: {', '.join(missing)}", file=sys.stderr)
        return 2

    if settings.shopware_mode.lower() != "live":
        print("SHOPWARE_MODE is not live; running read-only live smoke test without changing app mode.")

    client = ShopWareClient(settings)
    try:
        response = client.request("GET", "/api/v1/tenants")
    except (ExternalServiceError, ExternalServiceNotConfiguredError) as exc:
        print(f"Shop-Ware live smoke test failed: {exc}", file=sys.stderr)
        return 1

    count = _tenant_count(response)
    tenant_seen = _configured_tenant_seen(response, settings.shopware_tenant_id)

    print("Shop-Ware live smoke test passed.")
    print("Read-only endpoint: GET /api/v1/tenants")
    if count is not None:
        print(f"Tenants returned: {count}")
    if tenant_seen is not None:
        print(f"Configured tenant returned: {tenant_seen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
