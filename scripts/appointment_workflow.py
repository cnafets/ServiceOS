"""Exercise the local appointment workflow end to end.

Run while the FastAPI server is listening on http://127.0.0.1:8000:

    python scripts/appointment_workflow.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            return response.status, json.loads(response_body) if response_body else None
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        parsed = json.loads(response_body) if response_body else None
        return exc.code, parsed


def assert_status(actual: int, expected: int, step: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{step} expected HTTP {expected}, got HTTP {actual}.")


def main() -> int:
    start_time = (datetime.now(UTC) + timedelta(days=30)).replace(second=0, microsecond=0)
    end_time = start_time + timedelta(hours=2)
    overlap_start_time = start_time + timedelta(hours=1)
    overlap_end_time = start_time + timedelta(hours=3)
    updated_start_time = start_time + timedelta(hours=3)
    updated_end_time = start_time + timedelta(hours=5)

    original_payload = {
        "customer_name": "Jane Driver",
        "customer_phone": "555-0100",
        "customer_address": "123 Main St, Charlotte, NC",
        "vehicle_year": 2018,
        "vehicle_make": "Toyota",
        "vehicle_model": "Camry",
        "service_description": "No-start diagnostic",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "priority": "standard",
        "required_tools": "scan tool, battery tester",
        "parts_status": "not_checked",
        "communication_status": "awaiting_confirmation",
    }
    overlapping_payload = {
        **original_payload,
        "customer_name": "Overlap Test",
        "start_time": overlap_start_time.isoformat(),
        "end_time": overlap_end_time.isoformat(),
    }
    update_payload = {
        "service_description": "Updated no-start diagnostic and battery test",
        "start_time": updated_start_time.isoformat(),
        "end_time": updated_end_time.isoformat(),
        "parts_status": "not_needed",
        "communication_status": "confirmed",
        "notes": "Customer confirmed later arrival window.",
    }

    print("1. Creating appointment...")
    status, created = request_json("POST", "/api/v1/appointments", original_payload)
    assert_status(status, 201, "create appointment")
    appointment_id = created["id"]
    print(f"   Created appointment {appointment_id} with status {created['status']}.")

    print("2. Retrieving appointment...")
    status, retrieved = request_json("GET", f"/api/v1/appointments/{appointment_id}")
    assert_status(status, 200, "retrieve appointment")
    print(f"   Retrieved appointment for {retrieved['customer_name']}.")

    print("3. Confirming overlapping appointment fails...")
    status, overlap_response = request_json("POST", "/api/v1/appointments", overlapping_payload)
    assert_status(status, 409, "overlapping appointment")
    print(f"   Overlap rejected with detail: {overlap_response['detail']}")

    print("4. Updating original appointment...")
    status, updated = request_json("PATCH", f"/api/v1/appointments/{appointment_id}", update_payload)
    assert_status(status, 200, "update appointment")
    print(f"   Updated appointment status is {updated['status']}.")

    print("5. Cancelling appointment...")
    status, cancelled = request_json("DELETE", f"/api/v1/appointments/{appointment_id}")
    assert_status(status, 200, "cancel appointment")
    print(f"   Cancelled appointment status is {cancelled['status']}.")

    print("6. Confirming list reflects the final state...")
    status, appointments = request_json("GET", "/api/v1/appointments")
    assert_status(status, 200, "list appointments")
    final = next(item for item in appointments if item["id"] == appointment_id)
    if final["status"] != "cancelled":
        raise RuntimeError(f"Expected appointment {appointment_id} to be cancelled, got {final['status']}.")
    print(f"   Appointment list contains appointment {appointment_id} with status cancelled.")

    print("\nWorkflow complete.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nWorkflow failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
