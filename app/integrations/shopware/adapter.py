import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.core.exceptions import ExternalServiceNotConfiguredError
from app.integrations.shopware.client import ShopWareClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShopWareSyncResult:
    success: bool
    remote_id: str | None = None
    raw_response: dict[str, Any] | None = None
    error: str | None = None


class ShopWareAppointmentAdapter:
    """Appointment-specific adapter over the reusable Shop-Ware client."""

    def __init__(self, settings: Settings, client: ShopWareClient) -> None:
        self.settings = settings
        self.client = client

    def create(self, local_id: int, payload: dict[str, Any]) -> ShopWareSyncResult:
        if self._is_mock_mode:
            return self._mock_result("create", local_id)
        path = self._required_path(self.settings.shopware_appointment_create_path, "SHOPWARE_APPOINTMENT_CREATE_PATH")
        return self._send("POST", path, payload=payload)

    def update(self, remote_id: str, payload: dict[str, Any]) -> ShopWareSyncResult:
        if self._is_mock_mode:
            return self._mock_result("update", remote_id)
        path = self._required_path(self.settings.shopware_appointment_update_path, "SHOPWARE_APPOINTMENT_UPDATE_PATH")
        return self._send("PATCH", self._format_path(path, remote_id), payload=payload, fallback_remote_id=remote_id)

    def cancel(self, remote_id: str) -> ShopWareSyncResult:
        if self._is_mock_mode:
            return self._mock_result("cancel", remote_id)
        path = self._required_path(self.settings.shopware_appointment_cancel_path, "SHOPWARE_APPOINTMENT_CANCEL_PATH")
        return self._send("DELETE", self._format_path(path, remote_id), fallback_remote_id=remote_id)

    def search_customers(self, query: str) -> dict[str, Any]:
        return self._search(self.settings.shopware_customer_search_path, query)

    def search_vehicles(self, query: str) -> dict[str, Any]:
        return self._search(self.settings.shopware_vehicle_search_path, query)

    def search_repair_orders(self, query: str) -> dict[str, Any]:
        return self._search(self.settings.shopware_repair_order_search_path, query)

    @property
    def _is_mock_mode(self) -> bool:
        return self.settings.shopware_mode.lower() == "mock"

    def _send(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        fallback_remote_id: str | None = None,
    ) -> ShopWareSyncResult:
        try:
            kwargs = {"json": payload} if payload is not None else {}
            response = self.client.request(method, path, **kwargs)
            remote_id = self._extract_field(response, self.settings.shopware_appointment_id_field) or fallback_remote_id
            return ShopWareSyncResult(success=True, remote_id=remote_id, raw_response=response)
        except Exception as exc:
            logger.exception("Shop-Ware appointment sync failed method=%s path=%s", method, path)
            return ShopWareSyncResult(success=False, error=str(exc))

    def _search(self, configured_path: str | None, query: str) -> dict[str, Any]:
        if self._is_mock_mode:
            return {"items": [], "mode": "mock"}
        path = self._required_path(configured_path, "Shop-Ware search path")
        return self.client.request("GET", path, params={"q": query})

    def _required_path(self, path: str | None, env_name: str) -> str:
        if not path:
            raise ExternalServiceNotConfiguredError(f"{env_name} must be configured for live Shop-Ware mode.")
        return path

    def _format_path(self, path: str, remote_id: str) -> str:
        return path.format(appointment_id=remote_id, id=remote_id)

    def _extract_field(self, response: dict[str, Any], field_path: str) -> str | None:
        current: Any = response
        for part in field_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return str(current) if current is not None else None

    def _mock_result(self, action: str, identifier: int | str) -> ShopWareSyncResult:
        remote_id = str(identifier) if str(identifier).startswith("mock-sw-") else f"mock-sw-{identifier}"
        response = {"id": remote_id, "mode": "mock", "action": action}
        logger.info("Shop-Ware mock %s response=%s", action, response)
        return ShopWareSyncResult(success=True, remote_id=remote_id, raw_response=response)
