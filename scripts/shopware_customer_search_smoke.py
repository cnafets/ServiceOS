"""Read-only live Shop-Ware customer search smoke test.

Loads credentials from .env and performs only:

    GET /api/v1/tenants/{tenant_id}/customers

Optionally set SHOPWARE_CUSTOMER_SMOKE_QUERY to search by email, phone, or last
name. The default query is intentionally unlikely to match a real customer.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, ExternalServiceNotConfiguredError
from app.integrations.shopware.adapter import ShopWareCustomerAdapter
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
        print("SHOPWARE_MODE is not live; running read-only live customer search without changing app mode.")

    query = os.getenv("SHOPWARE_CUSTOMER_SMOKE_QUERY", "YNM_SMOKE_TEST_NO_MATCH")
    adapter = ShopWareCustomerAdapter(settings, ShopWareClient(settings))

    try:
        response = adapter.search(query, page=1, per_page=5)
    except (ExternalServiceError, ExternalServiceNotConfiguredError) as exc:
        print(f"Shop-Ware customer search smoke test failed: {exc}", file=sys.stderr)
        return 1

    print("Shop-Ware customer search smoke test passed.")
    print(f"Read-only endpoint: GET /api/v1/tenants/{settings.shopware_tenant_id}/customers")
    print(f"Search query: {query}")
    result_count = _count(response)
    if result_count is not None:
        print(f"Customers returned: {result_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

