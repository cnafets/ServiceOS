import pytest

from app.schemas.intake import IntakeCustomerData, IntakeData, IntakeVehicleData
from app.schemas.shopware import ShopWareCustomerCreate, ShopWareVehicleCreate
from app.services.intake import IntakeService


class FakeCustomerAdapter:
    def __init__(self, search_responses=None):
        self.search_responses = list(search_responses or [])
        self.search_calls = []
        self.create_calls = []

    def search(self, query=None, **kwargs):
        self.search_calls.append({"query": query, **kwargs})
        if self.search_responses:
            return self.search_responses.pop(0)
        return {"results": []}

    def create(self, payload: ShopWareCustomerCreate):
        self.create_calls.append(payload)
        return {"id": 42, "first_name": payload.first_name, "last_name": payload.last_name}


class FakeVehicleAdapter:
    def __init__(self, lookup_response=None):
        self.lookup_response = lookup_response or {"results": []}
        self.lookup_calls = []
        self.create_calls = []

    def lookup_by_vin(self, vin, **kwargs):
        self.lookup_calls.append(vin)
        return self.lookup_response

    def create(self, payload: ShopWareVehicleCreate):
        self.create_calls.append(payload)
        return {"id": 21, "vin": payload.vin, "customer_ids": payload.customer_ids}


def intake_data() -> IntakeData:
    return IntakeData(
        customer=IntakeCustomerData(
            full_name="Jane Driver",
            email="jane@example.com",
            address="123 Main St",
            city="Charlotte",
            state="NC",
            zip="28202",
        ),
        phone="(555) 010-0000",
        vin="1FMPU16W14LB56648",
        concern="No-start diagnostic",
        vehicle=IntakeVehicleData(year="2004", make="Ford", model="Expedition"),
    )


def test_intake_reuses_existing_customer_and_vehicle_without_creating_duplicates():
    customers = FakeCustomerAdapter(search_responses=[{"results": [{"id": 42, "phone": "5550100000"}]}])
    vehicles = FakeVehicleAdapter(lookup_response={"results": [{"id": 21, "vin": "1FMPU16W14LB56648"}]})
    service = IntakeService(customers, vehicles)

    result = service.resolve_customer_and_vehicle(intake_data())

    assert result.customer_id == 42
    assert result.vehicle_id == 21
    assert result.customer_created is False
    assert result.vehicle_created is False
    assert customers.create_calls == []
    assert vehicles.create_calls == []
    assert customers.search_calls[0]["phone_number"] == "5550100000"
    assert vehicles.lookup_calls == ["1FMPU16W14LB56648"]


def test_intake_creates_customer_and_vehicle_when_no_matches_exist():
    customers = FakeCustomerAdapter()
    vehicles = FakeVehicleAdapter()
    service = IntakeService(customers, vehicles)

    result = service.resolve_customer_and_vehicle(intake_data())

    assert result.customer_id == 42
    assert result.vehicle_id == 21
    assert result.customer_created is True
    assert result.vehicle_created is True
    assert len(customers.create_calls) == 1
    assert customers.create_calls[0].first_name == "Jane"
    assert customers.create_calls[0].last_name == "Driver"
    assert customers.create_calls[0].phone == "5550100000"
    assert customers.create_calls[0].phones[0].number == "5550100000"
    assert len(vehicles.create_calls) == 1
    assert vehicles.create_calls[0].vin == "1FMPU16W14LB56648"
    assert vehicles.create_calls[0].make == "Ford"
    assert vehicles.create_calls[0].customer_ids == [42]


def test_intake_integration_test_marker_is_added_to_supported_create_payloads():
    data = intake_data()
    data.integration_test_marker = "YNM Integration Test marker"
    customers = FakeCustomerAdapter()
    vehicles = FakeVehicleAdapter()
    service = IntakeService(customers, vehicles)

    service.resolve_customer_and_vehicle(data)

    assert customers.create_calls[0].detail.startswith("YNM Integration Test marker")
    assert vehicles.create_calls[0].detail == "YNM Integration Test marker"


def test_intake_reuses_existing_customer_and_creates_missing_vehicle():
    customers = FakeCustomerAdapter(search_responses=[{"results": [{"id": 99, "last_name": "Driver"}]}])
    vehicles = FakeVehicleAdapter()
    service = IntakeService(customers, vehicles)

    result = service.resolve_customer_and_vehicle(intake_data())

    assert result.customer_id == 99
    assert result.vehicle_id == 21
    assert result.customer_created is False
    assert result.vehicle_created is True
    assert customers.create_calls == []
    assert vehicles.create_calls[0].customer_ids == [99]


def test_intake_raises_when_vehicle_must_be_created_without_required_make():
    data = intake_data()
    data.vehicle = IntakeVehicleData(vin=data.vin)
    customers = FakeCustomerAdapter(search_responses=[{"results": [{"id": 42}]}])
    vehicles = FakeVehicleAdapter()
    service = IntakeService(customers, vehicles)

    with pytest.raises(ValueError, match="Vehicle make is required"):
        service.resolve_customer_and_vehicle(data)

    assert vehicles.create_calls == []
