from typing import Any

from app.core.config import Settings
from app.core.exceptions import ExternalServiceNotConfiguredError
from app.core.logging import get_logger
from app.core.time import rfc3339_datetime
from app.integrations.shopware.adapter import ShopWareRepairOrderAdapter
from app.schemas.intake import IntakeData
from app.schemas.shopware import ShopWareRepairOrderCreate, ShopWareRepairOrderUpdate

logger = get_logger(__name__)


class RepairOrderService:
    def __init__(self, settings: Settings, repair_order_adapter: ShopWareRepairOrderAdapter) -> None:
        self.settings = settings
        self.repair_order_adapter = repair_order_adapter

    def create(self, payload: ShopWareRepairOrderCreate) -> dict[str, Any]:
        logger.info("Repair Order Create Started")
        result = self.repair_order_adapter.create(payload)
        logger.info("Repair Order Create Completed", extra={"repair_order_id": self._required_id(result)})
        return result

    def retrieve(self, repair_order_id: int) -> dict[str, Any]:
        return self.repair_order_adapter.retrieve(repair_order_id)

    def search(self, **filters: Any) -> dict[str, Any]:
        return self.repair_order_adapter.search(**filters)

    def update(self, repair_order_id: int, payload: ShopWareRepairOrderUpdate) -> dict[str, Any]:
        return self.repair_order_adapter.update(repair_order_id, payload)

    def get_or_create_for_intake(
        self,
        data: IntakeData,
        *,
        customer_id: int,
        vehicle_id: int,
    ) -> tuple[dict[str, Any], bool]:
        logger.info("Repair Order Resolution Started", extra={"customer_id": customer_id, "vehicle_id": vehicle_id})
        existing = self._find_existing_open_repair_order(customer_id=customer_id, vehicle_id=vehicle_id)
        if existing is not None:
            logger.info("Repair Order Found", extra={"repair_order_id": self._required_id(existing)})
            return existing, False

        created = self.create(self._create_payload(data, customer_id=customer_id, vehicle_id=vehicle_id))
        return created, True

    def _find_existing_open_repair_order(self, *, customer_id: int, vehicle_id: int) -> dict[str, Any] | None:
        for status in ("estimate", "in_progress"):
            logger.info("Repair Order Search Started", extra={"status": status})
            response = self.repair_order_adapter.search(
                customer_id=customer_id,
                vehicle_id=vehicle_id,
                status=status,
                page=1,
                per_page=10,
            )
            match = self._first_result(response)
            if match is not None:
                return match
        return None

    def _create_payload(self, data: IntakeData, *, customer_id: int, vehicle_id: int) -> ShopWareRepairOrderCreate:
        if self.settings.shopware_default_shop_id is None:
            raise ExternalServiceNotConfiguredError(
                "SHOPWARE_DEFAULT_SHOP_ID must be configured to create Shop-Ware repair orders."
            )
        return ShopWareRepairOrderCreate(
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            shop_id=self.settings.shopware_default_shop_id,
            technician_id=self.settings.shopware_default_staff_id,
            customer_concern=data.concern,
            detail=self._detail(data),
            due_in_at=self._due_in_at(data),
            preferred_contact_type=self._preferred_contact_type(data),
            customer_source="Integration Test" if data.integration_test_marker else "Intake",
        )

    def _due_in_at(self, data: IntakeData) -> str | None:
        if data.requested_appointment is None or data.requested_appointment.start_time is None:
            return None
        return rfc3339_datetime(data.requested_appointment.start_time, self.settings.app_local_timezone)

    def _detail(self, data: IntakeData) -> str:
        detail = "Created from normalized intake workflow."
        if data.integration_test_marker:
            return f"{data.integration_test_marker}\n{detail}"
        return detail

    def _preferred_contact_type(self, data: IntakeData) -> str | None:
        if data.customer.email:
            return "email"
        if data.phone:
            return "text"
        return None

    def _first_result(self, response: dict[str, Any]) -> dict[str, Any] | None:
        results = response.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                return first
        return None

    def _required_id(self, entity: dict[str, Any]) -> int:
        identifier = entity.get("id")
        if identifier is None:
            raise ValueError("Resolved Shop-Ware repair order response did not include an id.")
        return int(identifier)
