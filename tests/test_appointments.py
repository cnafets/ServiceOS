from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import SchedulingConflictError
from app.db.session import Base
from app.integrations.shopware.adapter import ShopWareSyncResult
from app.models.appointment import SyncStatus
from app.schemas.appointment import AppointmentCreate
from app.services.appointments import AppointmentService


class MockShopWareAppointmentAdapter:
    def create(self, local_id, payload):
        return ShopWareSyncResult(success=True, remote_id=f"mock-sw-{local_id}")

    def update(self, remote_id, payload):
        return ShopWareSyncResult(success=True, remote_id=remote_id)

    def cancel(self, remote_id):
        return ShopWareSyncResult(success=True, remote_id=remote_id)


class FailingShopWareAppointmentAdapter:
    def create(self, local_id, payload):
        return ShopWareSyncResult(success=False, error="Shop-Ware timeout")

    def update(self, remote_id, payload):
        return ShopWareSyncResult(success=False, error="Shop-Ware timeout")

    def cancel(self, remote_id):
        return ShopWareSyncResult(success=False, error="Shop-Ware timeout")


class FlakyShopWareAppointmentAdapter:
    def __init__(self):
        self.create_calls = 0

    def create(self, local_id, payload):
        self.create_calls += 1
        if self.create_calls == 1:
            return ShopWareSyncResult(success=False, error="Temporary outage")
        return ShopWareSyncResult(success=True, remote_id=f"mock-sw-{local_id}")

    def update(self, remote_id, payload):
        return ShopWareSyncResult(success=True, remote_id=remote_id)

    def cancel(self, remote_id):
        return ShopWareSyncResult(success=True, remote_id=remote_id)


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


def make_payload(start: datetime, end: datetime) -> AppointmentCreate:
    return AppointmentCreate(
        customer_name="Test Customer",
        customer_phone="555-0100",
        customer_address="123 Main St, Charlotte, NC",
        vehicle_year=2018,
        vehicle_make="Toyota",
        vehicle_model="Camry",
        service_description="Mobile diagnostic appointment",
        start_time=start,
        end_time=end,
        priority="standard",
    )


def test_create_appointment_stores_local_metadata(db_session):
    service = AppointmentService(db_session, MockShopWareAppointmentAdapter())
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    appointment = service.create(make_payload(start, start + timedelta(hours=2)))

    assert appointment.id is not None
    assert appointment.customer_name == "Test Customer"
    assert appointment.customer_address == "123 Main St, Charlotte, NC"
    assert appointment.shopware_appointment_id == f"mock-sw-{appointment.id}"
    assert appointment.sync_status == SyncStatus.SYNCED


def test_prevents_double_booking(db_session):
    service = AppointmentService(db_session, MockShopWareAppointmentAdapter())
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    service.create(make_payload(start, start + timedelta(hours=2)))

    with pytest.raises(SchedulingConflictError):
        service.create(make_payload(start + timedelta(minutes=30), start + timedelta(hours=3)))


def test_cancelled_appointment_does_not_block_time_slot(db_session):
    service = AppointmentService(db_session, MockShopWareAppointmentAdapter())
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    appointment = service.create(make_payload(start, start + timedelta(hours=2)))
    service.cancel(appointment.id)

    replacement = service.create(make_payload(start, start + timedelta(hours=2)))
    assert replacement.id != appointment.id


def test_sync_failure_keeps_local_appointment_pending(db_session):
    service = AppointmentService(db_session, FailingShopWareAppointmentAdapter())
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    appointment = service.create(make_payload(start, start + timedelta(hours=2)))

    assert appointment.id is not None
    assert appointment.shopware_appointment_id is None
    assert appointment.sync_status == SyncStatus.PENDING
    assert appointment.sync_error == "Shop-Ware timeout"


def test_retry_sync_updates_pending_appointment(db_session):
    adapter = FlakyShopWareAppointmentAdapter()
    service = AppointmentService(db_session, adapter)
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    appointment = service.create(make_payload(start, start + timedelta(hours=2)))

    retried = service.retry_sync(appointment.id)

    assert retried.sync_status == SyncStatus.SYNCED
    assert retried.sync_error is None
    assert retried.shopware_appointment_id == f"mock-sw-{appointment.id}"
    assert retried.sync_attempts == 2
