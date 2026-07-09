from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.intake import get_intake_workflow_service, router
from app.schemas.intake import IntakeWorkflowResult


class CapturingWorkflowService:
    def __init__(self):
        self.idempotency_key = None

    def execute(self, payload, idempotency_key=None):
        self.idempotency_key = idempotency_key
        return IntakeWorkflowResult(
            customer_id=42,
            vehicle_id=21,
            customer_created=True,
            vehicle_created=True,
            repair_order_id=77,
            repair_order_created=True,
            local_appointment_id=1,
            shopware_appointment_id="sw-appt-1",
            appointment_created=True,
            appointment_sync_status="synced",
        )


def test_intake_route_passes_idempotency_key_header():
    app = FastAPI()
    service = CapturingWorkflowService()
    app.dependency_overrides[get_intake_workflow_service] = lambda: service
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    response = client.post(
        "/api/v1/intake/workflows",
        headers={"Idempotency-Key": "header-key-1"},
        json={
            "customer": {"full_name": "Jane Driver", "email": "jane@example.com"},
            "phone": "5550100000",
            "vin": "1FMPU16W14LB56648",
            "concern": "No-start diagnostic",
            "requested_appointment": {
                "start_time": "2026-07-10T14:00:00Z",
                "end_time": "2026-07-10T16:00:00Z",
                "priority": "standard",
            },
            "vehicle": {"year": "2004", "make": "Ford", "model": "Expedition"},
        },
    )

    assert response.status_code == 201
    assert service.idempotency_key == "header-key-1"
