from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.exceptions import SchedulingConflictError
from app.integrations.shopware.adapter import ShopWareAppointmentAdapter, ShopWareSyncResult
from app.models.appointment import Appointment, AppointmentStatus, SyncStatus
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate


class AppointmentService:
    def __init__(self, db: Session, shopware_adapter: ShopWareAppointmentAdapter) -> None:
        self.db = db
        self.shopware_adapter = shopware_adapter

    def create(self, data: AppointmentCreate) -> Appointment:
        self._ensure_available(data.start_time, data.end_time)
        appointment = Appointment(
            **data.model_dump(),
            status=AppointmentStatus.SCHEDULED,
            sync_status=SyncStatus.PENDING,
        )
        self.db.add(appointment)
        self.db.flush()
        result = self.shopware_adapter.create(appointment.id, self._to_shopware_payload(data.model_dump()))
        self._apply_sync_result(appointment, result)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def update(self, appointment_id: int, data: AppointmentUpdate) -> Appointment | None:
        appointment = self.get(appointment_id)
        if appointment is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        start_time = updates.get("start_time", appointment.start_time)
        end_time = updates.get("end_time", appointment.end_time)
        if start_time >= end_time:
            raise ValueError("end_time must be after start_time")
        self._ensure_available(start_time, end_time, exclude_id=appointment.id)

        for key, value in updates.items():
            setattr(appointment, key, value)

        appointment.status = AppointmentStatus.UPDATED
        result = self._sync_existing_appointment(appointment, self._to_shopware_payload(updates))
        self._apply_sync_result(appointment, result)

        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def cancel(self, appointment_id: int) -> Appointment | None:
        appointment = self.get(appointment_id)
        if appointment is None:
            return None

        appointment.status = AppointmentStatus.CANCELLED
        result = self._sync_existing_appointment(appointment, self._to_shopware_payload({}))
        self._apply_sync_result(appointment, result)

        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def retry_sync(self, appointment_id: int) -> Appointment | None:
        appointment = self.get(appointment_id)
        if appointment is None:
            return None

        result = self._sync_existing_appointment(appointment, self._to_shopware_payload(self._appointment_payload(appointment)))
        self._apply_sync_result(appointment, result)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def get(self, appointment_id: int) -> Appointment | None:
        return self.db.get(Appointment, appointment_id)

    def list(self) -> list[Appointment]:
        statement = select(Appointment).order_by(Appointment.start_time)
        return list(self.db.scalars(statement).all())

    def _ensure_available(self, start_time: datetime, end_time: datetime, exclude_id: int | None = None) -> None:
        statement = select(Appointment).where(
            and_(
                Appointment.status != AppointmentStatus.CANCELLED,
                Appointment.start_time < end_time,
                Appointment.end_time > start_time,
            )
        )
        if exclude_id is not None:
            statement = statement.where(Appointment.id != exclude_id)

        conflict = self.db.scalars(statement).first()
        if conflict:
            raise SchedulingConflictError(
                f"Requested window overlaps appointment {conflict.id} from {conflict.start_time} to {conflict.end_time}."
            )

    def _to_shopware_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = data.copy()
        for field in ("start_time", "end_time"):
            if isinstance(payload.get(field), datetime):
                payload[field] = payload[field].isoformat()
        return payload

    def _sync_existing_appointment(self, appointment: Appointment, payload: dict[str, Any]) -> ShopWareSyncResult:
        if appointment.status == AppointmentStatus.CANCELLED:
            if appointment.shopware_appointment_id is None:
                return ShopWareSyncResult(success=True)
            return self.shopware_adapter.cancel(appointment.shopware_appointment_id)
        if appointment.shopware_appointment_id is None:
            return self.shopware_adapter.create(appointment.id, self._appointment_payload(appointment))
        return self.shopware_adapter.update(appointment.shopware_appointment_id, payload)

    def _apply_sync_result(self, appointment: Appointment, result: ShopWareSyncResult) -> None:
        appointment.sync_attempts = (appointment.sync_attempts or 0) + 1
        appointment.last_sync_at = datetime.now(UTC)
        if result.success:
            appointment.sync_status = SyncStatus.SYNCED
            appointment.sync_error = None
            if result.remote_id:
                appointment.shopware_appointment_id = result.remote_id
            return

        appointment.sync_status = SyncStatus.PENDING
        appointment.sync_error = result.error

    def _appointment_payload(self, appointment: Appointment) -> dict[str, Any]:
        return self._to_shopware_payload(
            {
                "customer_name": appointment.customer_name,
                "customer_phone": appointment.customer_phone,
                "customer_email": appointment.customer_email,
                "customer_address": appointment.customer_address,
                "vehicle_year": appointment.vehicle_year,
                "vehicle_make": appointment.vehicle_make,
                "vehicle_model": appointment.vehicle_model,
                "service_description": appointment.service_description,
                "start_time": appointment.start_time,
                "end_time": appointment.end_time,
                "priority": appointment.priority,
                "required_tools": appointment.required_tools,
                "parts_status": appointment.parts_status,
                "communication_status": appointment.communication_status,
                "notes": appointment.notes,
                "status": appointment.status,
            }
        )
