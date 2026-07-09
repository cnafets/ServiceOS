import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.core.exceptions import ExternalServiceNotConfiguredError
from app.integrations.shopware.client import ShopWareClient
from app.schemas.shopware import ShopWareAppointmentCreate, ShopWareAppointmentUpdate

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
        path = self._format_path(self.settings.shopware_appointment_create_path)
        shopware_payload = self._appointment_create_payload(payload)
        return self._send("POST", path, payload=shopware_payload)

    def update(self, remote_id: str, payload: dict[str, Any]) -> ShopWareSyncResult:
        if self._is_mock_mode:
            return self._mock_result("update", remote_id)
        path = self._format_path(self.settings.shopware_appointment_update_path, appointment_id=remote_id)
        shopware_payload = self._appointment_update_payload(payload)
        return self._send("PUT", path, payload=shopware_payload, fallback_remote_id=remote_id)

    def cancel(self, remote_id: str) -> ShopWareSyncResult:
        if self._is_mock_mode:
            return self._mock_result("cancel", remote_id)
        path = self._format_path(self.settings.shopware_appointment_cancel_path, appointment_id=remote_id)
        return self._send("DELETE", path, fallback_remote_id=remote_id)

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
        path = self._format_path(self._required_path(configured_path, "Shop-Ware search path"))
        return self.client.request("GET", path, params=self._search_params(path, query))

    def _required_path(self, path: str | None, env_name: str) -> str:
        if not path:
            raise ExternalServiceNotConfiguredError(f"{env_name} must be configured for live Shop-Ware mode.")
        return path

    def _format_path(self, path: str, appointment_id: str | None = None) -> str:
        if self.settings.shopware_tenant_id is None:
            raise ExternalServiceNotConfiguredError("SHOPWARE_TENANT_ID must be configured for live Shop-Ware mode.")
        return path.format(
            tenant_id=self.settings.shopware_tenant_id,
            appointment_id=appointment_id,
            id=appointment_id,
        )

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

    def _appointment_create_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.settings.shopware_default_shop_id is None:
            raise ExternalServiceNotConfiguredError(
                "SHOPWARE_DEFAULT_SHOP_ID must be configured to create Shop-Ware appointments."
            )
        data = ShopWareAppointmentCreate(
            shop_id=self.settings.shopware_default_shop_id,
            staff_id=self.settings.shopware_default_staff_id,
            title=self._title(payload),
            description=self._description(payload),
            start_at=payload["start_time"],
            end_at=payload.get("end_time"),
            repair_order_id=payload.get("repair_order_id"),
        )
        return data.model_dump(mode="json", exclude_none=True)

    def _appointment_update_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = ShopWareAppointmentUpdate(
            shop_id=self.settings.shopware_default_shop_id,
            staff_id=self.settings.shopware_default_staff_id,
            title=self._title(payload) if self._has_title_source(payload) else None,
            description=self._description(payload) if payload else None,
            start_at=payload.get("start_time"),
            end_at=payload.get("end_time"),
            repair_order_id=payload.get("repair_order_id"),
        )
        return data.model_dump(mode="json", exclude_none=True)

    def _title(self, payload: dict[str, Any]) -> str:
        service = payload.get("service_description")
        customer = payload.get("customer_name")
        if service and customer:
            return f"{customer} - {service}"
        return service or customer or "Mobile service appointment"

    def _description(self, payload: dict[str, Any]) -> str | None:
        parts = [
            payload.get("service_description"),
            payload.get("customer_address"),
            payload.get("vehicle_make") or payload.get("vehicle_model"),
            payload.get("notes"),
        ]
        description = "\n".join(str(part) for part in parts if part)
        return description or None

    def _has_title_source(self, payload: dict[str, Any]) -> bool:
        return bool(payload.get("service_description") or payload.get("customer_name"))

    def _search_params(self, path: str, query: str) -> dict[str, Any]:
        params: dict[str, Any] = {"page": 1, "per_page": 30}
        if path.endswith("/customers"):
            if "@" in query:
                params["email"] = query
            elif any(char.isdigit() for char in query):
                params["phone_number"] = "".join(char for char in query if char.isdigit())
            else:
                params["last_name"] = query
        elif path.endswith("/vehicles"):
            params["vin"] = query
        elif path.endswith("/repair_orders"):
            params["number"] = query
        return params
