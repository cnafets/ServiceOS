import logging
import time
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, ExternalServiceNotConfiguredError

logger = logging.getLogger(__name__)


class ShopWareClient:
    """Reusable Shop-Ware HTTP client for all entity adapters."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        if not self.settings.shopware_api_token:
            raise ExternalServiceNotConfiguredError("SHOPWARE_API_TOKEN is required for Shop-Ware API calls.")
        token_value = (
            f"{self.settings.shopware_auth_scheme} {self.settings.shopware_api_token}"
            if self.settings.shopware_auth_scheme
            else self.settings.shopware_api_token
        )
        return {self.settings.shopware_auth_header_name: token_value, "Content-Type": "application/json"}

    def _client(self) -> httpx.Client:
        if not self.settings.shopware_base_url:
            raise ExternalServiceNotConfiguredError("SHOPWARE_BASE_URL is required for Shop-Ware API calls.")
        return httpx.Client(
            base_url=self.settings.shopware_base_url,
            timeout=self.settings.shopware_timeout_seconds,
            headers=self._headers(),
        )

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        attempts = max(1, self.settings.shopware_retry_attempts)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                safe_kwargs = {key: value for key, value in kwargs.items() if key.lower() != "headers"}
                logger.info("Shop-Ware request attempt=%s method=%s path=%s kwargs=%s", attempt, method, path, safe_kwargs)
                with self._client() as client:
                    response = client.request(method, path, **kwargs)
                    body_preview = response.text[:1000] if response.text else ""
                    logger.info(
                        "Shop-Ware response attempt=%s method=%s path=%s status=%s body=%s",
                        attempt,
                        method,
                        path,
                        response.status_code,
                        body_preview,
                    )
                    response.raise_for_status()
                    if response.content:
                        return response.json()
                    return {}
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                logger.warning(
                    "Shop-Ware request failed attempt=%s/%s method=%s path=%s error=%s",
                    attempt,
                    attempts,
                    method,
                    path,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(self.settings.shopware_retry_backoff_seconds * attempt)

        raise ExternalServiceError(f"Shop-Ware API request failed after {attempts} attempt(s): {last_error}")
