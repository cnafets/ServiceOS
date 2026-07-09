from app.core.config import settings
from app.integrations.shopware.adapter import ShopWareAppointmentAdapter
from app.integrations.shopware.client import ShopWareClient


def get_shopware_client() -> ShopWareClient:
    return ShopWareClient(settings)


def get_shopware_appointment_adapter() -> ShopWareAppointmentAdapter:
    return ShopWareAppointmentAdapter(settings, get_shopware_client())
