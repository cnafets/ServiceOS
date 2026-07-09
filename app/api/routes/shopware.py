from typing import Any

from fastapi import APIRouter, Depends, Query

from app.integrations.shopware.adapter import ShopWareCustomerAdapter, ShopWareRepairOrderAdapter, ShopWareVehicleAdapter
from app.integrations.shopware.dependencies import (
    get_shopware_customer_adapter,
    get_shopware_repair_order_adapter,
    get_shopware_vehicle_adapter,
)
from app.schemas.shopware import (
    ShopWareCustomerCreate,
    ShopWareCustomerUpdate,
    ShopWareRepairOrderCreate,
    ShopWareRepairOrderUpdate,
    ShopWareVehicleCreate,
    ShopWareVehicleUpdate,
)

router = APIRouter(prefix="/shopware", tags=["shopware"])


@router.get("/customers/search")
def search_customers(
    q: str | None = Query(default=None, min_length=1),
    last_name: str | None = Query(default=None),
    email: str | None = Query(default=None),
    phone_number: str | None = Query(default=None),
    customer_type: str | None = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    shopware_adapter: ShopWareCustomerAdapter = Depends(get_shopware_customer_adapter),
) -> dict[str, Any]:
    return shopware_adapter.search(
        q,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
        customer_type=customer_type,
        page=page,
        per_page=per_page,
    )


@router.post("/customers")
def create_customer(
    payload: ShopWareCustomerCreate,
    shopware_adapter: ShopWareCustomerAdapter = Depends(get_shopware_customer_adapter),
) -> dict[str, Any]:
    return shopware_adapter.create(payload)


@router.get("/customers/{customer_id}")
def retrieve_customer(
    customer_id: int,
    shopware_adapter: ShopWareCustomerAdapter = Depends(get_shopware_customer_adapter),
) -> dict[str, Any]:
    return shopware_adapter.retrieve(customer_id)


@router.put("/customers/{customer_id}")
def update_customer(
    customer_id: int,
    payload: ShopWareCustomerUpdate,
    shopware_adapter: ShopWareCustomerAdapter = Depends(get_shopware_customer_adapter),
) -> dict[str, Any]:
    return shopware_adapter.update(customer_id, payload)


@router.get("/vehicles/search")
def search_vehicles(
    q: str | None = Query(default=None, min_length=1),
    vin: str | None = Query(default=None, min_length=1),
    customer_id: int | None = Query(default=None, ge=1),
    updated_after: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    shopware_adapter: ShopWareVehicleAdapter = Depends(get_shopware_vehicle_adapter),
) -> dict[str, Any]:
    return shopware_adapter.search(
        q,
        vin=vin,
        customer_id=customer_id,
        updated_after=updated_after,
        page=page,
        per_page=per_page,
    )


@router.get("/vehicles/vin/{vin}")
def lookup_vehicle_by_vin(
    vin: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    shopware_adapter: ShopWareVehicleAdapter = Depends(get_shopware_vehicle_adapter),
) -> dict[str, Any]:
    return shopware_adapter.lookup_by_vin(vin, page=page, per_page=per_page)


@router.get("/vehicles/customer/{customer_id}")
def search_vehicles_by_customer(
    customer_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    shopware_adapter: ShopWareVehicleAdapter = Depends(get_shopware_vehicle_adapter),
) -> dict[str, Any]:
    return shopware_adapter.search_by_customer(customer_id, page=page, per_page=per_page)


@router.post("/vehicles")
def create_vehicle(
    payload: ShopWareVehicleCreate,
    shopware_adapter: ShopWareVehicleAdapter = Depends(get_shopware_vehicle_adapter),
) -> dict[str, Any]:
    return shopware_adapter.create(payload)


@router.get("/vehicles/{vehicle_id}")
def retrieve_vehicle(
    vehicle_id: int,
    shopware_adapter: ShopWareVehicleAdapter = Depends(get_shopware_vehicle_adapter),
) -> dict[str, Any]:
    return shopware_adapter.retrieve(vehicle_id)


@router.put("/vehicles/{vehicle_id}")
def update_vehicle(
    vehicle_id: int,
    payload: ShopWareVehicleUpdate,
    shopware_adapter: ShopWareVehicleAdapter = Depends(get_shopware_vehicle_adapter),
) -> dict[str, Any]:
    return shopware_adapter.update(vehicle_id, payload)


@router.get("/repair-orders/search")
def search_repair_orders(
    shop_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    vehicle_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    number: int | None = Query(default=None),
    updated_after: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    shopware_adapter: ShopWareRepairOrderAdapter = Depends(get_shopware_repair_order_adapter),
) -> dict[str, Any]:
    return shopware_adapter.search(
        shop_id=shop_id,
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        status=status,
        number=number,
        updated_after=updated_after,
        page=page,
        per_page=per_page,
    )


@router.post("/repair-orders")
def create_repair_order(
    payload: ShopWareRepairOrderCreate,
    shopware_adapter: ShopWareRepairOrderAdapter = Depends(get_shopware_repair_order_adapter),
) -> dict[str, Any]:
    return shopware_adapter.create(payload)


@router.get("/repair-orders/{repair_order_id}")
def retrieve_repair_order(
    repair_order_id: int,
    shopware_adapter: ShopWareRepairOrderAdapter = Depends(get_shopware_repair_order_adapter),
) -> dict[str, Any]:
    return shopware_adapter.retrieve(repair_order_id)


@router.put("/repair-orders/{repair_order_id}")
def update_repair_order(
    repair_order_id: int,
    payload: ShopWareRepairOrderUpdate,
    shopware_adapter: ShopWareRepairOrderAdapter = Depends(get_shopware_repair_order_adapter),
) -> dict[str, Any]:
    return shopware_adapter.update(repair_order_id, payload)
