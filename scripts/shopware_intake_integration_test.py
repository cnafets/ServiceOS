"""Live Shop-Ware intake workflow integration test.

This script creates clearly marked test customer, vehicle, repair order, and
appointment records. It refuses to run unless:

    INTEGRATION_TEST_MODE=true
    SHOPWARE_MODE=live
    --confirm-live-write is provided

The script verifies each created record with read-back requests and cancels the
Shop-Ware appointment by default. Customer, vehicle, and repair order deletion
is not documented in the provided OpenAPI file, so those records must be
manually cleaned up by searching for the printed integration test marker.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.session import Base
from app.integrations.shopware.adapter import (
    ShopWareAppointmentAdapter,
    ShopWareCustomerAdapter,
    ShopWareRepairOrderAdapter,
    ShopWareVehicleAdapter,
)
from app.integrations.shopware.client import ShopWareClient
from app.schemas.intake import IntakeCustomerData, IntakeData, IntakeRequestedAppointment, IntakeVehicleData
from app.services.intake_workflow import IntakeWorkflowService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and verify a live Shop-Ware intake integration test workflow.")
    parser.add_argument(
        "--confirm-live-write",
        action="store_true",
        help="Required. Confirms this script may create marked test records in live Shop-Ware.",
    )
    parser.add_argument(
        "--keep-appointment",
        action="store_true",
        help="Do not cancel the created Shop-Ware appointment after verification.",
    )
    return parser.parse_args()


def build_intake(marker: str) -> IntakeData:
    unique = uuid4().hex[:10]
    phone_suffix = str(uuid4().int)[-4:]
    start = datetime.now(UTC) + timedelta(days=21)
    start = start.replace(minute=0, second=0, microsecond=0)
    return IntakeData(
        customer=IntakeCustomerData(
            first_name="YNM",
            last_name=f"Integration Test {unique}",
            email=f"ynm.integration.{unique}@example.com",
            address="Integration Test Address",
            city="Charlotte",
            state="NC",
            zip="28202",
        ),
        phone=f"555010{phone_suffix}",
        vin=f"TESTVIN{unique.upper()}"[:17],
        concern=f"{marker} - No-start diagnostic test concern",
        requested_appointment=IntakeRequestedAppointment(
            start_time=start,
            end_time=start + timedelta(hours=1),
            priority="integration_test",
        ),
        vehicle=IntakeVehicleData(
            year="2004",
            make="Ford",
            model=f"Integration Test {unique}",
            color="TEST",
            plate=f"T{unique[:6].upper()}",
        ),
        integration_test_marker=marker,
    )


def make_service(settings: Settings) -> tuple[IntakeWorkflowService, ShopWareAppointmentAdapter, ShopWareCustomerAdapter, ShopWareVehicleAdapter, ShopWareRepairOrderAdapter]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    client = ShopWareClient(settings)
    customer_adapter = ShopWareCustomerAdapter(settings, client)
    vehicle_adapter = ShopWareVehicleAdapter(settings, client)
    repair_order_adapter = ShopWareRepairOrderAdapter(settings, client)
    appointment_adapter = ShopWareAppointmentAdapter(settings, client)
    return (
        IntakeWorkflowService(
            session,
            settings,
            customer_adapter,
            vehicle_adapter,
            repair_order_adapter,
            appointment_adapter,
        ),
        appointment_adapter,
        customer_adapter,
        vehicle_adapter,
        repair_order_adapter,
    )


def require_safe_mode(settings: Settings, confirmed: bool) -> None:
    missing = [
        name
        for name, value in {
            "SHOPWARE_BASE_URL": settings.shopware_base_url,
            "SHOPWARE_API_PARTNER_ID": settings.shopware_api_partner_id,
            "SHOPWARE_API_SECRET": settings.shopware_api_secret,
            "SHOPWARE_TENANT_ID": settings.shopware_tenant_id,
            "SHOPWARE_DEFAULT_SHOP_ID": settings.shopware_default_shop_id,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required Shop-Ware settings: {', '.join(missing)}")
    if settings.shopware_mode.lower() != "live":
        raise RuntimeError("SHOPWARE_MODE must be live for this integration test.")
    if not settings.integration_test_mode:
        raise RuntimeError("INTEGRATION_TEST_MODE must be true for this integration test.")
    if not confirmed:
        raise RuntimeError("--confirm-live-write is required because this script creates live Shop-Ware test records.")


def require_id(entity: dict, name: str) -> int | str:
    identifier = entity.get("id")
    if identifier is None:
        raise RuntimeError(f"Verified {name} response did not include id.")
    return identifier


def main() -> int:
    args = parse_args()
    settings = Settings()
    try:
        require_safe_mode(settings, args.confirm_live_write)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    marker = f"YNM Integration Test {datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')} {uuid4().hex[:8]}"
    service, appointment_adapter, customer_adapter, vehicle_adapter, repair_order_adapter = make_service(settings)
    result = service.execute(build_intake(marker))

    verified_customer = customer_adapter.retrieve(result.customer_id)
    verified_vehicle = vehicle_adapter.retrieve(result.vehicle_id)
    verified_repair_order = repair_order_adapter.retrieve(result.repair_order_id)
    verified_appointment = None
    cleanup: dict[str, str | bool | None] = {
        "appointment_cancel_attempted": False,
        "appointment_cancelled": None,
        "note": "Customer, vehicle, and repair order deletion is not documented; clean them manually by marker.",
    }

    if result.shopware_appointment_id:
        verified_appointment = appointment_adapter.retrieve(result.shopware_appointment_id)
        if not args.keep_appointment:
            cleanup["appointment_cancel_attempted"] = True
            cancel_result = appointment_adapter.cancel(result.shopware_appointment_id)
            cleanup["appointment_cancelled"] = cancel_result.success
            cleanup["appointment_cancel_error"] = cancel_result.error

    output = {
        "marker": marker,
        "ids": {
            "customer_id": result.customer_id,
            "vehicle_id": result.vehicle_id,
            "repair_order_id": result.repair_order_id,
            "local_appointment_id": result.local_appointment_id,
            "shopware_appointment_id": result.shopware_appointment_id,
        },
        "creation_flags": {
            "customer_created": result.customer_created,
            "vehicle_created": result.vehicle_created,
            "repair_order_created": result.repair_order_created,
            "appointment_created": result.appointment_created,
        },
        "verified": {
            "customer_id": require_id(verified_customer, "customer"),
            "vehicle_id": require_id(verified_vehicle, "vehicle"),
            "repair_order_id": require_id(verified_repair_order, "repair_order"),
            "appointment_id": require_id(verified_appointment, "appointment") if verified_appointment else None,
        },
        "cleanup": cleanup,
        "manual_cleanup": [
            "Search Shop-Ware customers for last name prefix 'Integration Test' or the marker above.",
            "Search vehicles by the generated VIN printed in Shop-Ware/customer records if needed.",
            "Search repair orders by customer/vehicle and marker in detail/customer source.",
            "The appointment is cancelled automatically unless --keep-appointment was used.",
        ],
    }
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
