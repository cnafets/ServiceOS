from app.core.config import settings
from app.integrations.shopware.adapter import (
    ShopWareAppointmentAdapter,
    ShopWareCustomerAdapter,
    ShopWareRepairOrderAdapter,
    ShopWareVehicleAdapter,
)
from app.integrations.shopware.client import ShopWareClient


def get_shopware_client() -> ShopWareClient:
    return ShopWareClient(settings)


def get_shopware_appointment_adapter() -> ShopWareAppointmentAdapter:
    return ShopWareAppointmentAdapter(settings, get_shopware_client())


def get_shopware_customer_adapter() -> ShopWareCustomerAdapter:
    return ShopWareCustomerAdapter(settings, get_shopware_client())


def get_shopware_vehicle_adapter() -> ShopWareVehicleAdapter:
    return ShopWareVehicleAdapter(settings, get_shopware_client())


def get_shopware_repair_order_adapter() -> ShopWareRepairOrderAdapter:
    return ShopWareRepairOrderAdapter(settings, get_shopware_client())
