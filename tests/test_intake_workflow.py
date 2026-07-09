from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.session import Base
from app.integrations.shopware.adapter import ShopWareSyncResult
from app.schemas.intake import IntakeCustomerData, IntakeData, IntakeRequestedAppointment, IntakeVehicleData
from app.schemas.shopware import ShopWareCustomerCreate, ShopWareRepairOrderCreate, ShopWareVehicleCreate
from app.services.intake_workflow import IntakeWorkflowService


class FakeCustomerAdapter:
    def __init__(self, search_responses=None):
        self.search_responses = list(search_responses or [])
        self.create_calls = []

    def search(self, query=None, **kwargs):
        if self.search_responses:
            return self.search_responses.pop(0)
        return {"results": []}

    def create(self, payload: ShopWareCustomerCreate):
        self.create_calls.append(payload)
        return {"id": 42}


class FakeVehicleAdapter:
    def __init__(self, lookup_response=None):
        self.lookup_response = lookup_response or {"results": []}
        self.create_calls = []

    def lookup_by_vin(self, vin, **kwargs):
        return self.lookup_response

    def create(self, payload: ShopWareVehicleCreate):
        self.create_calls.append(payload)
        return {"id": 21}


class FakeRepairOrderAdapter:
    def __init__(self, search_responses=None):
        self.search_responses = list(search_responses or [])
        self.create_calls = []

    def search(self, **kwargs):
        if self.search_responses:
            return self.search_responses.pop(0)
        return {"results": []}

    def create(self, payload: ShopWareRepairOrderCreate):
        self.create_calls.append(payload)
        return {"id": 77, "state": "estimate"}


class FakeAppointmentAdapter:
    def __init__(self):
        self.create_calls = []

    def create(self, local_id, payload):
        self.create_calls.append((local_id, payload))
        return ShopWareSyncResult(success=True, remote_id=f"sw-appt-{local_id}")

    def update(self, remote_id, payload):
        return ShopWareSyncResult(success=True, remote_id=remote_id)

    def cancel(self, remote_id):
        return ShopWareSyncResult(success=True, remote_id=remote_id)


class ResumableCustomerAdapter(FakeCustomerAdapter):
    def __init__(self):
        super().__init__()
        self.created = False

    def search(self, query=None, **kwargs):
        return {"results": [{"id": 42}]} if self.created else {"results": []}

    def create(self, payload: ShopWareCustomerCreate):
        self.created = True
        return super().create(payload)


class ResumableVehicleAdapter(FakeVehicleAdapter):
    def __init__(self):
        super().__init__()
        self.created = False

    def lookup_by_vin(self, vin, **kwargs):
        return {"results": [{"id": 21}]} if self.created else {"results": []}

    def create(self, payload: ShopWareVehicleCreate):
        self.created = True
        return super().create(payload)


class ResumableRepairOrderAdapter(FakeRepairOrderAdapter):
    def __init__(self):
        super().__init__()
        self.created = False

    def search(self, **kwargs):
        return {"results": [{"id": 77, "state": "estimate"}]} if self.created else {"results": []}

    def create(self, payload: ShopWareRepairOrderCreate):
        self.created = True
        return super().create(payload)


class FailsOnceAppointmentAdapter(FakeAppointmentAdapter):
    def __init__(self):
        super().__init__()
        self.failed = False

    def create(self, local_id, payload):
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated appointment sync crash")
        return super().create(local_id, payload)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def workflow_data() -> IntakeData:
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
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
        requested_appointment=IntakeRequestedAppointment(
            start_time=start,
            end_time=start + timedelta(hours=2),
            priority="standard",
        ),
        vehicle=IntakeVehicleData(year="2004", make="Ford", model="Expedition"),
    )


def workflow_service(db_session, customers, vehicles, repair_orders, appointments):
    settings = Settings(shopware_default_shop_id=7, shopware_default_staff_id=3)
    return IntakeWorkflowService(db_session, settings, customers, vehicles, repair_orders, appointments)


def test_intake_workflow_creates_customer_vehicle_repair_order_and_appointment(db_session):
    appointments = FakeAppointmentAdapter()
    repair_orders = FakeRepairOrderAdapter()
    service = workflow_service(
        db_session,
        FakeCustomerAdapter(),
        FakeVehicleAdapter(),
        repair_orders,
        appointments,
    )

    result = service.execute(workflow_data())

    assert result.customer_id == 42
    assert result.vehicle_id == 21
    assert result.repair_order_id == 77
    assert result.customer_created is True
    assert result.vehicle_created is True
    assert result.repair_order_created is True
    assert result.appointment_created is True
    assert result.local_appointment_id == 1
    assert result.shopware_appointment_id == "sw-appt-1"
    assert result.appointment_sync_status == "synced"
    assert appointments.create_calls[0][1]["repair_order_id"] == 77
    assert repair_orders.create_calls[0].model_dump(mode="json")["due_in_at"].endswith("Z")


def test_intake_workflow_integration_marker_reaches_repair_order_and_appointment(db_session):
    data = workflow_data()
    data.integration_test_marker = "YNM Integration Test marker"
    repair_orders = FakeRepairOrderAdapter()
    appointments = FakeAppointmentAdapter()
    service = workflow_service(
        db_session,
        FakeCustomerAdapter(),
        FakeVehicleAdapter(),
        repair_orders,
        appointments,
    )

    service.execute(data)

    assert repair_orders.create_calls[0].detail.startswith("YNM Integration Test marker")
    assert repair_orders.create_calls[0].customer_source == "Integration Test"
    assert appointments.create_calls[0][1]["notes"] == "YNM Integration Test marker"


def test_intake_workflow_converts_naive_due_in_at_to_configured_timezone(db_session):
    data = workflow_data()
    data.requested_appointment.start_time = datetime(2026, 7, 10, 10, 0)
    data.requested_appointment.end_time = datetime(2026, 7, 10, 11, 0)
    repair_orders = FakeRepairOrderAdapter()
    service = workflow_service(
        db_session,
        FakeCustomerAdapter(),
        FakeVehicleAdapter(),
        repair_orders,
        FakeAppointmentAdapter(),
    )

    service.execute(data)

    assert repair_orders.create_calls[0].model_dump(mode="json")["due_in_at"] == "2026-07-10T14:00:00Z"


def test_intake_workflow_reuses_existing_customer_vehicle_and_repair_order(db_session):
    repair_orders = FakeRepairOrderAdapter(search_responses=[{"results": [{"id": 77, "state": "estimate"}]}])
    service = workflow_service(
        db_session,
        FakeCustomerAdapter(search_responses=[{"results": [{"id": 42}]}]),
        FakeVehicleAdapter(lookup_response={"results": [{"id": 21}]}),
        repair_orders,
        FakeAppointmentAdapter(),
    )

    result = service.execute(workflow_data())

    assert result.customer_created is False
    assert result.vehicle_created is False
    assert result.repair_order_created is False
    assert result.repair_order_id == 77
    assert repair_orders.create_calls == []


def test_intake_workflow_requires_requested_appointment(db_session):
    data = workflow_data()
    data.requested_appointment = None
    service = workflow_service(
        db_session,
        FakeCustomerAdapter(),
        FakeVehicleAdapter(),
        FakeRepairOrderAdapter(),
        FakeAppointmentAdapter(),
    )

    with pytest.raises(ValueError, match="requested_appointment.start_time is required"):
        service.execute(data)


def test_intake_workflow_replays_cached_result_for_repeated_idempotency_key(db_session):
    customers = FakeCustomerAdapter()
    vehicles = FakeVehicleAdapter()
    repair_orders = FakeRepairOrderAdapter()
    appointments = FakeAppointmentAdapter()
    service = workflow_service(db_session, customers, vehicles, repair_orders, appointments)

    first = service.execute(workflow_data(), idempotency_key="intake-key-1")
    second = service.execute(workflow_data(), idempotency_key="intake-key-1")

    assert second == first
    assert len(customers.create_calls) == 1
    assert len(vehicles.create_calls) == 1
    assert len(repair_orders.create_calls) == 1
    assert len(appointments.create_calls) == 1


def test_intake_workflow_accepts_idempotency_key_from_request_body(db_session):
    data = workflow_data()
    data.idempotency_key = "body-key-1"
    appointments = FakeAppointmentAdapter()
    service = workflow_service(
        db_session,
        FakeCustomerAdapter(),
        FakeVehicleAdapter(),
        FakeRepairOrderAdapter(),
        appointments,
    )

    first = service.execute(data)
    second = service.execute(data)

    assert second == first
    assert len(appointments.create_calls) == 1


def test_intake_workflow_rejects_same_idempotency_key_for_different_payload(db_session):
    service = workflow_service(
        db_session,
        FakeCustomerAdapter(),
        FakeVehicleAdapter(),
        FakeRepairOrderAdapter(),
        FakeAppointmentAdapter(),
    )
    service.execute(workflow_data(), idempotency_key="intake-key-2")
    changed = workflow_data()
    changed.concern = "Different concern"

    with pytest.raises(ValueError, match="different request payload"):
        service.execute(changed, idempotency_key="intake-key-2")


def test_intake_workflow_retry_after_partial_failure_does_not_duplicate_external_records(db_session):
    customers = ResumableCustomerAdapter()
    vehicles = ResumableVehicleAdapter()
    repair_orders = ResumableRepairOrderAdapter()
    appointments = FailsOnceAppointmentAdapter()
    service = workflow_service(db_session, customers, vehicles, repair_orders, appointments)

    with pytest.raises(RuntimeError, match="simulated appointment sync crash"):
        service.execute(workflow_data(), idempotency_key="intake-key-3")

    result = service.execute(workflow_data(), idempotency_key="intake-key-3")

    assert result.customer_id == 42
    assert result.vehicle_id == 21
    assert result.repair_order_id == 77
    assert result.customer_created is False
    assert result.vehicle_created is False
    assert result.repair_order_created is False
    assert len(customers.create_calls) == 1
    assert len(vehicles.create_calls) == 1
    assert len(repair_orders.create_calls) == 1
    assert len(appointments.create_calls) == 1
