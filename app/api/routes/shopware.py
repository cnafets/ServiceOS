from fastapi import APIRouter, Depends, Query

from app.integrations.shopware.adapter import ShopWareAppointmentAdapter
from app.integrations.shopware.dependencies import get_shopware_appointment_adapter

router = APIRouter(prefix="/shopware", tags=["shopware"])


@router.get("/customers/search")
def search_customers(
    q: str = Query(min_length=1),
    shopware_adapter: ShopWareAppointmentAdapter = Depends(get_shopware_appointment_adapter),
):
    return shopware_adapter.search_customers(q)


@router.get("/vehicles/search")
def search_vehicles(
    q: str = Query(min_length=1),
    shopware_adapter: ShopWareAppointmentAdapter = Depends(get_shopware_appointment_adapter),
):
    return shopware_adapter.search_vehicles(q)


@router.get("/repair-orders/search")
def search_repair_orders(
    q: str = Query(min_length=1),
    shopware_adapter: ShopWareAppointmentAdapter = Depends(get_shopware_appointment_adapter),
):
    return shopware_adapter.search_repair_orders(q)
