import time
from typing import Any

from app.core.logging import get_logger
from app.integrations.shopware.adapter import ShopWareCustomerAdapter, ShopWareVehicleAdapter
from app.schemas.intake import IntakeData, IntakeResolution
from app.schemas.shopware import ShopWareCustomerCreate, ShopWareCustomerPhone, ShopWareVehicleCreate

logger = get_logger(__name__)


class IntakeService:
    """Resolve normalized intake data into existing or newly created Shop-Ware records."""

    def __init__(
        self,
        customer_adapter: ShopWareCustomerAdapter,
        vehicle_adapter: ShopWareVehicleAdapter,
    ) -> None:
        self.customer_adapter = customer_adapter
        self.vehicle_adapter = vehicle_adapter

    def resolve_customer_and_vehicle(self, data: IntakeData) -> IntakeResolution:
        start = time.perf_counter()
        logger.info("Intake Started")
        customer, customer_created = self._get_or_create_customer(data)
        customer_id = self._required_id(customer, "customer")

        vehicle, vehicle_created = self._get_or_create_vehicle(data, customer_id)
        vehicle_id = self._required_id(vehicle, "vehicle")

        logger.info(
            "Intake Completed",
            extra={
                "customer_id": customer_id,
                "vehicle_id": vehicle_id,
                "customer_created": customer_created,
                "vehicle_created": vehicle_created,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        return IntakeResolution(
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            customer_created=customer_created,
            vehicle_created=vehicle_created,
        )

    def _get_or_create_customer(self, data: IntakeData) -> tuple[dict[str, Any], bool]:
        logger.info("Customer Resolution Started")
        existing = self._find_existing_customer(data)
        if existing is not None:
            logger.info("Customer Found", extra={"customer_id": self._required_id(existing, "customer")})
            return existing, False

        created = self.customer_adapter.create(self._customer_create_payload(data))
        logger.info("Customer Created", extra={"customer_id": self._required_id(created, "customer")})
        return created, True

    def _find_existing_customer(self, data: IntakeData) -> dict[str, Any] | None:
        phone = self._clean_phone(data.phone)
        if phone:
            logger.info("Customer Search Started", extra={"lookup_type": "phone"})
            match = self._first_result(self.customer_adapter.search(phone_number=phone))
            if match is not None:
                return match

        if data.customer.email:
            logger.info("Customer Search Started", extra={"lookup_type": "email"})
            match = self._first_result(self.customer_adapter.search(email=data.customer.email))
            if match is not None:
                return match

        if data.customer.last_name:
            logger.info("Customer Search Started", extra={"lookup_type": "last_name"})
            match = self._first_result(self.customer_adapter.search(last_name=data.customer.last_name))
            if match is not None:
                return match

        _, last_name = self._name_parts(data)
        if last_name:
            logger.info("Customer Search Started", extra={"lookup_type": "last_name"})
            return self._first_result(self.customer_adapter.search(last_name=last_name))
        return None

    def _get_or_create_vehicle(self, data: IntakeData, customer_id: int) -> tuple[dict[str, Any], bool]:
        logger.info("Vehicle Search Started", extra={"lookup_type": "vin"})
        existing = self._first_result(self.vehicle_adapter.lookup_by_vin(data.vin))
        if existing is not None:
            logger.info("Vehicle Found", extra={"vehicle_id": self._required_id(existing, "vehicle")})
            return existing, False

        created = self.vehicle_adapter.create(self._vehicle_create_payload(data, customer_id))
        logger.info("Vehicle Created", extra={"vehicle_id": self._required_id(created, "vehicle")})
        return created, True

    def _customer_create_payload(self, data: IntakeData) -> ShopWareCustomerCreate:
        first_name, last_name = self._name_parts(data)
        phone = self._clean_phone(data.phone)
        phones = None
        if phone:
            phones = [ShopWareCustomerPhone(number=phone, preferred=True, show_on_ro=True)]

        return ShopWareCustomerCreate(
            first_name=first_name,
            last_name=last_name,
            email=data.customer.email,
            phone=phone,
            phones=phones,
            address=data.customer.address,
            city=data.customer.city,
            state=data.customer.state,
            zip=data.customer.zip,
            detail=self._detail(data),
        )

    def _vehicle_create_payload(self, data: IntakeData, customer_id: int) -> ShopWareVehicleCreate:
        vehicle = data.vehicle
        make = vehicle.make if vehicle and vehicle.make else None
        if not make:
            raise ValueError("Vehicle make is required to create a Shop-Ware vehicle when VIN lookup has no match.")

        return ShopWareVehicleCreate(
            vin=data.vin,
            year=vehicle.year if vehicle else None,
            make=make,
            model=vehicle.model if vehicle else None,
            engine=vehicle.engine if vehicle else None,
            color=vehicle.color if vehicle else None,
            plate=vehicle.plate if vehicle else None,
            detail=data.integration_test_marker,
            customer_ids=[customer_id],
        )

    def _detail(self, data: IntakeData) -> str:
        if data.integration_test_marker:
            return f"{data.integration_test_marker}\n{data.concern}"
        return data.concern

    def _name_parts(self, data: IntakeData) -> tuple[str | None, str | None]:
        first_name = data.customer.first_name
        last_name = data.customer.last_name
        if first_name or last_name:
            return first_name, last_name

        if not data.customer.full_name:
            return None, None
        parts = data.customer.full_name.strip().split()
        if not parts:
            return None, None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], " ".join(parts[1:])

    def _clean_phone(self, phone: str | None) -> str | None:
        if not phone:
            return None
        digits = "".join(char for char in phone if char.isdigit())
        return digits or None

    def _first_result(self, response: dict[str, Any]) -> dict[str, Any] | None:
        results = response.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                return first
        return None

    def _required_id(self, entity: dict[str, Any], entity_name: str) -> int:
        identifier = entity.get("id")
        if identifier is None:
            raise ValueError(f"Resolved Shop-Ware {entity_name} response did not include an id.")
        return int(identifier)
