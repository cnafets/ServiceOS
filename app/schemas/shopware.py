from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ShopWareIntegratorTag(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    taggable_type: str | None = None
    taggable_id: int | None = None
    name: str | None = None
    value: str | int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ShopWarePagination(BaseModel):
    limit: int | None = None
    limited: bool | None = None
    total_count: int | None = None
    current_page: int | None = None
    total_pages: int | None = None


class ShopWareAppointmentCreate(BaseModel):
    shop_id: int
    start_at: datetime
    staff_id: int | None = None
    repair_order_id: int | None = None
    title: str | None = None
    description: str | None = None
    end_at: datetime | None = None


class ShopWareAppointmentUpdate(BaseModel):
    shop_id: int | None = None
    start_at: datetime | None = None
    staff_id: int | None = None
    repair_order_id: int | None = None
    title: str | None = None
    description: str | None = None
    end_at: datetime | None = None


class ShopWareAppointment(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    shop_id: int | None = None
    staff_id: int | None = None
    repair_order_id: int | None = None
    description: str | None = None
    title: str | None = None
    integrator_tags: list[ShopWareIntegratorTag] = Field(default_factory=list)
    start_at: datetime | None = None
    end_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ShopWareAppointmentList(ShopWarePagination):
    results: list[ShopWareAppointment] = Field(default_factory=list)


class ShopWareCustomer(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    customer_type: str | None = None
    business_name: str | None = None


class ShopWareVehicle(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    plate: str | None = None
    vin: str | None = None
    year: str | int | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None
    color: str | None = None


class ShopWareRepairOrder(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    number: int | str | None = None
    state: str | None = None
    status_id: int | None = None
    customer_id: int | None = None
    vehicle_id: int | None = None
    shop_id: int | None = None
    detail: str | None = None
    customer_concern: str | None = None
    due_in_at: datetime | None = None
    due_out_at: datetime | None = None


class ShopWareRecommendation(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    description: str | None = None
    approved: str | None = None
    repair_order_id: int | None = None
    quick_price_cents: float | None = None
    service: dict[str, Any] | None = None


class ShopWareWebhook(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    url: str
    events: list[str]
    format: str | None = None

