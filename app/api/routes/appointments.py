import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import SchedulingConflictError
from app.db.session import get_db
from app.integrations.shopware.adapter import ShopWareAppointmentAdapter
from app.integrations.shopware.dependencies import get_shopware_appointment_adapter
from app.schemas.appointment import (
    AppointmentCancelResponse,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
)
from app.services.appointments import AppointmentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/appointments", tags=["appointments"])


def get_appointment_service(
    db: Session = Depends(get_db),
    shopware_adapter: ShopWareAppointmentAdapter = Depends(get_shopware_appointment_adapter),
) -> AppointmentService:
    return AppointmentService(db, shopware_adapter)


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    service: AppointmentService = Depends(get_appointment_service),
):
    try:
        return service.create(payload)
    except SchedulingConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[AppointmentRead])
def list_appointments(service: AppointmentService = Depends(get_appointment_service)):
    return service.list()


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, service: AppointmentService = Depends(get_appointment_service)):
    appointment = service.get(appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    service: AppointmentService = Depends(get_appointment_service),
):
    try:
        appointment = service.update(appointment_id, payload)
    except SchedulingConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return appointment


@router.delete("/{appointment_id}", response_model=AppointmentCancelResponse)
def cancel_appointment(appointment_id: int, service: AppointmentService = Depends(get_appointment_service)):
    appointment = service.cancel(appointment_id)

    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return AppointmentCancelResponse(id=appointment.id, status=appointment.status)


@router.post("/{appointment_id}/sync", response_model=AppointmentRead)
def retry_appointment_sync(appointment_id: int, service: AppointmentService = Depends(get_appointment_service)):
    appointment = service.retry_sync(appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return appointment
