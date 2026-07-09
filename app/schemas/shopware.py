from datetime import date, datetime
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
    start_at: datetime | str
    staff_id: int | None = None
    repair_order_id: int | None = None
    title: str | None = None
    description: str | None = None
    end_at: datetime | str | None = None


class ShopWareAppointmentUpdate(BaseModel):
    shop_id: int | None = None
    start_at: datetime | str | None = None
    staff_id: int | None = None
    repair_order_id: int | None = None
    title: str | None = None
    description: str | None = None
    end_at: datetime | str | None = None


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
    shop_ids: list[int] | None = None
    origin_shop_id: int | None = None


class ShopWareCustomerPhone(BaseModel):
    number: str | None = None
    label: str | None = None
    preferred: bool | None = None
    show_on_ro: bool | None = None


class ShopWareCustomerCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    detail: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    marketing_ok: bool | None = None
    phones: list[ShopWareCustomerPhone] | None = None
    shop_id: int | None = None
    customer_type: str | None = None
    date_of_birth: date | None = None
    business_name: str | None = None
    fleet_id: str | None = None


class ShopWareCustomerUpdate(ShopWareCustomerCreate):
    pass


class ShopWareCustomerList(ShopWarePagination):
    results: list[ShopWareCustomer] = Field(default_factory=list)


class ShopWareVehicle(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    plate: str | None = None
    detail: str | None = None
    fleet_number: str | None = None
    vin: str | None = None
    year: str | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None
    production_date: date | datetime | str | None = None
    registration_exp_date: date | datetime | str | None = None
    color: str | None = None
    customer_ids: list[int] | None = None
    integrator_tags: list[ShopWareIntegratorTag] = Field(default_factory=list)


class ShopWareVehicleCreate(BaseModel):
    plate: str | None = None
    production_date: date | None = None
    registration_exp_date: date | None = None
    detail: str | None = None
    fleet_number: str | None = None
    vin: str | None = None
    year: str | None = None
    make: str = Field(min_length=1)
    model: str | None = None
    engine: str | None = None
    color: str | None = None
    customer_ids: list[int] | None = None


class ShopWareVehicleUpdate(BaseModel):
    plate: str | None = None
    production_date: date | None = None
    registration_exp_date: date | None = None
    detail: str | None = None
    fleet_number: str | None = None
    vin: str | None = None
    year: str | None = None
    make: str | None = Field(default=None, min_length=1)
    model: str | None = None
    engine: str | None = None
    color: str | None = None
    customer_ids: list[int] | None = None


class ShopWareVehicleList(ShopWarePagination):
    results: list[ShopWareVehicle] = Field(default_factory=list)


class ShopWareRepairOrder(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    number: int | str | None = None
    odometer: int | None = None
    odometer_out: int | None = None
    state: str | None = None
    status_id: int | None = None
    customer_id: int | None = None
    technician_id: int | None = None
    advisor_id: int | None = None
    vehicle_id: int | None = None
    shop_id: int | None = None
    detail: str | None = None
    preferred_contact_type: str | None = None
    taxable: bool | None = None
    customer_source: str | None = None
    customer_concern: str | None = None
    vehicle_use: str | None = None
    fleet_po: str | None = None
    due_in_at: datetime | str | None = None
    due_out_at: datetime | None = None


class ShopWareRepairOrderCreate(BaseModel):
    number: int | None = None
    odometer: int | None = None
    customer_id: int
    technician_id: int | None = None
    advisor_id: int | None = None
    vehicle_id: int | None = None
    label_id: int | None = None
    detail: str | None = None
    preferred_contact_type: str | None = None
    shop_id: int
    taxable: bool | None = None
    due_in_at: datetime | str | None = None
    customer_source: str | None = None
    fleet_po: str | None = None
    customer_concern: str | None = None
    vehicle_use: str | None = None


class ShopWareRepairOrderUpdate(BaseModel):
    number: int | None = None
    odometer: int | None = None
    customer_id: int | None = None
    technician_id: int | None = None
    advisor_id: int | None = None
    vehicle_id: int | None = None
    label_id: int | None = None
    detail: str | None = None
    preferred_contact_type: str | None = None
    shop_id: int | None = None
    taxable: bool | None = None
    due_in_at: datetime | None = None
    customer_source: str | None = None
    fleet_po: str | None = None
    customer_concern: str | None = None
    vehicle_use: str | None = None


class ShopWareRepairOrderList(ShopWarePagination):
    results: list[ShopWareRepairOrder] = Field(default_factory=list)


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
