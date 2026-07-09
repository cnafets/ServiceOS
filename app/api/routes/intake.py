from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import SchedulingConflictError
from app.db.session import get_db
from app.integrations.shopware.adapter import (
    ShopWareAppointmentAdapter,
    ShopWareCustomerAdapter,
    ShopWareRepairOrderAdapter,
    ShopWareVehicleAdapter,
)
from app.integrations.shopware.dependencies import (
    get_shopware_appointment_adapter,
    get_shopware_customer_adapter,
    get_shopware_repair_order_adapter,
    get_shopware_vehicle_adapter,
)
from app.schemas.intake import IntakeData, IntakeWorkflowResult
from app.services.intake_workflow import IntakeWorkflowService

router = APIRouter(prefix="/intake", tags=["intake"])


def get_intake_workflow_service(
    db: Session = Depends(get_db),
    customer_adapter: ShopWareCustomerAdapter = Depends(get_shopware_customer_adapter),
    vehicle_adapter: ShopWareVehicleAdapter = Depends(get_shopware_vehicle_adapter),
    repair_order_adapter: ShopWareRepairOrderAdapter = Depends(get_shopware_repair_order_adapter),
    appointment_adapter: ShopWareAppointmentAdapter = Depends(get_shopware_appointment_adapter),
) -> IntakeWorkflowService:
    return IntakeWorkflowService(
        db,
        settings,
        customer_adapter,
        vehicle_adapter,
        repair_order_adapter,
        appointment_adapter,
    )


@router.post("/workflows", response_model=IntakeWorkflowResult, status_code=status.HTTP_201_CREATED)
def run_intake_workflow(
    payload: IntakeData,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: IntakeWorkflowService = Depends(get_intake_workflow_service),
) -> IntakeWorkflowResult:
    try:
        return service.execute(payload, idempotency_key=idempotency_key)
    except SchedulingConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
