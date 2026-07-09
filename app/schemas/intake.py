from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntakeCustomerData(BaseModel):
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None


class IntakeVehicleData(BaseModel):
    vin: str | None = None
    year: str | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None
    color: str | None = None
    plate: str | None = None


class IntakeRequestedAppointment(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    priority: str | None = None


class IntakeData(BaseModel):
    model_config = ConfigDict(extra="allow")

    customer: IntakeCustomerData
    phone: str | None = None
    vin: str = Field(min_length=1)
    concern: str = Field(min_length=1)
    requested_appointment: IntakeRequestedAppointment | None = None
    vehicle: IntakeVehicleData | None = None
    integration_test_marker: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)


class IntakeResolution(BaseModel):
    customer_id: int
    vehicle_id: int
    customer_created: bool
    vehicle_created: bool


class IntakeWorkflowResult(IntakeResolution):
    repair_order_id: int
    repair_order_created: bool
    local_appointment_id: int
    shopware_appointment_id: str | None = None
    appointment_created: bool
    appointment_sync_status: str
