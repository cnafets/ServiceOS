from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.appointment import AppointmentStatus, SyncStatus


class AppointmentBase(BaseModel):
    repair_order_id: int | None = None
    customer_name: str = Field(min_length=1, max_length=255)
    customer_phone: str | None = None
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    vehicle_year: int | None = Field(default=None, ge=1900, le=2100)
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    service_description: str = Field(min_length=1)
    start_time: datetime
    end_time: datetime
    priority: str | None = None
    required_tools: str | None = None
    parts_status: str | None = None
    communication_status: str | None = None
    notes: str | None = None

    @field_validator("end_time")
    @classmethod
    def end_time_must_follow_start_time(cls, end_time: datetime, info):
        start_time = info.data.get("start_time")
        if start_time and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1, max_length=255)
    customer_phone: str | None = None
    customer_email: EmailStr | None = None
    customer_address: str | None = None
    vehicle_year: int | None = Field(default=None, ge=1900, le=2100)
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    service_description: str | None = Field(default=None, min_length=1)
    start_time: datetime | None = None
    end_time: datetime | None = None
    priority: str | None = None
    required_tools: str | None = None
    parts_status: str | None = None
    communication_status: str | None = None
    notes: str | None = None

    @field_validator("end_time")
    @classmethod
    def end_time_must_follow_start_time(cls, end_time: datetime | None, info):
        start_time = info.data.get("start_time")
        if start_time and end_time and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class AppointmentRead(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shopware_appointment_id: str | None = None
    status: AppointmentStatus
    sync_status: SyncStatus
    sync_error: str | None = None
    sync_attempts: int
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AppointmentCancelResponse(BaseModel):
    id: int
    status: AppointmentStatus
