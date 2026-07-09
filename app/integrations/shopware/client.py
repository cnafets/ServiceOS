import time
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, ExternalServiceNotConfiguredError
from app.core.logging import get_logger
from app.core.metrics import record_retry, record_shopware_call

logger = get_logger(__name__)


class ShopWareClient:
    """Reusable Shop-Ware HTTP client for all entity adapters."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        if not self.settings.shopware_api_partner_id or not self.settings.shopware_api_secret:
            raise ExternalServiceNotConfiguredError(
                "SHOPWARE_API_PARTNER_ID and SHOPWARE_API_SECRET are required for live Shop-Ware API calls."
            )
        return {
            "X-Api-Partner-Id": self.settings.shopware_api_partner_id,
            "X-Api-Secret": self.settings.shopware_api_secret,
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.Client:
        if not self.settings.shopware_base_url:
            raise ExternalServiceNotConfiguredError("SHOPWARE_BASE_URL is required for Shop-Ware API calls.")
        return httpx.Client(
            base_url=self.settings.shopware_base_url,
            timeout=self.settings.shopware_timeout_seconds,
            headers=self._headers(),
            transport=self.transport,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        attempts = max(1, self.settings.shopware_retry_attempts)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                request_start = time.perf_counter()
                logger.info(
                    "Shop-Ware Request Started",
                    extra={"attempt": attempt, "http_method": method, "endpoint": path},
                )
                with self._client() as client:
                    response = client.request(method, path, **kwargs)
                    duration_ms = round((time.perf_counter() - request_start) * 1000, 2)
                    record_shopware_call(duration_ms, error=response.status_code >= 400)
                    logger.info(
                        "Shop-Ware Request Completed",
                        extra={
                            "attempt": attempt,
                            "http_method": method,
                            "endpoint": path,
                            "status_code": response.status_code,
                            "duration_ms": duration_ms,
                        },
                    )
                    response.raise_for_status()
                    if response.content:
                        return response.json()
                    return {}
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                duration_ms = round((time.perf_counter() - request_start) * 1000, 2)
                if not isinstance(exc, httpx.HTTPStatusError):
                    record_shopware_call(duration_ms, error=True)
                logger.warning(
                    "Shop-Ware Request Failed",
                    extra={
                        "attempt": attempt,
                        "max_attempts": attempts,
                        "http_method": method,
                        "endpoint": path,
                        "error_type": type(exc).__name__,
                    },
                )
                if attempt < attempts:
                    record_retry()
                    time.sleep(self.settings.shopware_retry_backoff_seconds * attempt)

        raise ExternalServiceError(f"Shop-Ware API request failed after {attempts} attempt(s): {self._format_error(last_error)}")

    def _format_error(self, error: Exception | None) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            response = error.response
            body = response.text[:1000] if response.text else ""
            return f"HTTP {response.status_code} {response.reason_phrase}: {body}"
        return str(error)
