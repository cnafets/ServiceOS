import time

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.shopware.adapter import (
    ShopWareAppointmentAdapter,
    ShopWareCustomerAdapter,
    ShopWareRepairOrderAdapter,
    ShopWareVehicleAdapter,
)
from app.schemas.appointment import AppointmentCreate
from app.schemas.intake import IntakeData, IntakeWorkflowResult
from app.services.appointments import AppointmentService
from app.services.idempotency import IdempotencyService
from app.services.intake import IntakeService
from app.services.repair_orders import RepairOrderService
from app.core.config import Settings

logger = get_logger(__name__)


class IntakeWorkflowService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        customer_adapter: ShopWareCustomerAdapter,
        vehicle_adapter: ShopWareVehicleAdapter,
        repair_order_adapter: ShopWareRepairOrderAdapter,
        appointment_adapter: ShopWareAppointmentAdapter,
    ) -> None:
        self.db = db
        self.settings = settings
        self.intake_service = IntakeService(customer_adapter, vehicle_adapter)
        self.repair_order_service = RepairOrderService(settings, repair_order_adapter)
        self.appointment_service = AppointmentService(db, appointment_adapter)
        self.idempotency_service = IdempotencyService(db, settings.idempotency_ttl_seconds)

    def execute(self, data: IntakeData, idempotency_key: str | None = None) -> IntakeWorkflowResult:
        effective_key = idempotency_key or data.idempotency_key
        if effective_key:
            existing = self.idempotency_service.get_completed_result(effective_key, data)
            if existing is not None:
                return existing

        try:
            result = self._execute_uncached(data, effective_key)
        except Exception:
            self.db.rollback()
            logger.exception("Intake Workflow Failed", extra={"idempotency_key": effective_key})
            raise

        if effective_key:
            self.idempotency_service.store_completed_result(effective_key, data, result)
        return result

    def _execute_uncached(self, data: IntakeData, idempotency_key: str | None = None) -> IntakeWorkflowResult:
        start = time.perf_counter()
        logger.info("Intake Workflow Started", extra={"idempotency_key": idempotency_key})

        resolution = self.intake_service.resolve_customer_and_vehicle(data)
        repair_order, repair_order_created = self.repair_order_service.get_or_create_for_intake(
            data,
            customer_id=resolution.customer_id,
            vehicle_id=resolution.vehicle_id,
        )
        repair_order_id = self._required_id(repair_order, "repair_order")

        appointment = self.appointment_service.create(self._appointment_payload(data, repair_order_id=repair_order_id))

        logger.info(
            "Intake Workflow Completed",
            extra={
                "customer_id": resolution.customer_id,
                "vehicle_id": resolution.vehicle_id,
                "repair_order_id": repair_order_id,
                "local_appointment_id": appointment.id,
                "appointment_sync_status": appointment.sync_status.value,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        result = IntakeWorkflowResult(
            customer_id=resolution.customer_id,
            vehicle_id=resolution.vehicle_id,
            customer_created=resolution.customer_created,
            vehicle_created=resolution.vehicle_created,
            repair_order_id=repair_order_id,
            repair_order_created=repair_order_created,
            local_appointment_id=appointment.id,
            shopware_appointment_id=appointment.shopware_appointment_id,
            appointment_created=True,
            appointment_sync_status=appointment.sync_status.value,
        )
        return result

    def _appointment_payload(self, data: IntakeData, *, repair_order_id: int) -> AppointmentCreate:
        if data.requested_appointment is None or data.requested_appointment.start_time is None:
            raise ValueError("requested_appointment.start_time is required to schedule an appointment.")
        if data.requested_appointment.end_time is None:
            raise ValueError("requested_appointment.end_time is required to schedule an appointment.")

        first_name, last_name = self.intake_service._name_parts(data)
        customer_name = " ".join(part for part in (first_name, last_name) if part) or "Unknown Customer"
        vehicle = data.vehicle
        return AppointmentCreate(
            repair_order_id=repair_order_id,
            customer_name=customer_name,
            customer_phone=data.phone,
            customer_email=data.customer.email,
            customer_address=self._customer_address(data),
            vehicle_year=self._vehicle_year(vehicle.year if vehicle else None),
            vehicle_make=vehicle.make if vehicle else None,
            vehicle_model=vehicle.model if vehicle else None,
            service_description=data.concern,
            start_time=data.requested_appointment.start_time,
            end_time=data.requested_appointment.end_time,
            priority=data.requested_appointment.priority,
            communication_status="intake_completed",
            notes=data.integration_test_marker,
        )

    def _customer_address(self, data: IntakeData) -> str | None:
        parts = [data.customer.address, data.customer.city, data.customer.state, data.customer.zip]
        address = ", ".join(part for part in parts if part)
        return address or None

    def _vehicle_year(self, value: str | None) -> int | None:
        if value is None:
            return None
        return int(value) if value.isdigit() else None

    def _required_id(self, entity: dict, entity_name: str) -> int:
        identifier = entity.get("id")
        if identifier is None:
            raise ValueError(f"Resolved Shop-Ware {entity_name} response did not include an id.")
        return int(identifier)
