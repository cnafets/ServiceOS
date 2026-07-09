import httpx

from app.core.config import Settings
from app.integrations.shopware.adapter import ShopWareAppointmentAdapter
from app.integrations.shopware.client import ShopWareClient


def live_settings() -> Settings:
    return Settings(
        shopware_mode="live",
        shopware_base_url="https://api.shop-ware.com",
        shopware_api_partner_id="partner-123",
        shopware_api_secret="secret-456",
        shopware_tenant_id=99,
        shopware_default_shop_id=7,
        shopware_default_staff_id=3,
        shopware_retry_attempts=1,
    )


def test_shopware_client_uses_official_auth_headers():
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["partner"] = request.headers.get("X-Api-Partner-Id")
        seen_headers["secret"] = request.headers.get("X-Api-Secret")
        return httpx.Response(200, json={"ok": True})

    client = ShopWareClient(live_settings(), transport=httpx.MockTransport(handler))

    response = client.request("GET", "/api/v1/tenants")

    assert response == {"ok": True}
    assert seen_headers == {"partner": "partner-123", "secret": "secret-456"}


def test_shopware_client_reports_response_body_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"error": "invalid appointment"})

    client = ShopWareClient(live_settings(), transport=httpx.MockTransport(handler))

    try:
        client.request("POST", "/api/v1/tenants/99/appointments", json={})
    except Exception as exc:
        assert "HTTP 422" in str(exc)
        assert "invalid appointment" in str(exc)
    else:
        raise AssertionError("Expected Shop-Ware request to fail.")


def test_appointment_adapter_uses_official_create_endpoint_and_payload():
    captured = {}

    class FakeClient:
        def request(self, method, path, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["json"] = kwargs["json"]
            return {
                "id": 123,
                "shop_id": 7,
                "staff_id": 3,
                "title": "Jane Driver - No-start diagnostic",
                "description": "No-start diagnostic",
                "start_at": "2026-07-10T14:00:00Z",
            }

    adapter = ShopWareAppointmentAdapter(live_settings(), FakeClient())
    result = adapter.create(
        1,
        {
            "customer_name": "Jane Driver",
            "service_description": "No-start diagnostic",
            "customer_address": "123 Main St",
            "start_time": "2026-07-10T14:00:00Z",
            "end_time": "2026-07-10T16:00:00Z",
        },
    )

    assert result.success is True
    assert result.remote_id == "123"
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/tenants/99/appointments"
    assert captured["json"]["shop_id"] == 7
    assert captured["json"]["staff_id"] == 3
    assert captured["json"]["start_at"] == "2026-07-10T14:00:00Z"
    assert captured["json"]["end_at"] == "2026-07-10T16:00:00Z"
    assert captured["json"]["title"] == "Jane Driver - No-start diagnostic"


def test_appointment_adapter_uses_official_update_and_delete_endpoints():
    calls = []

    class FakeClient:
        def request(self, method, path, **kwargs):
            calls.append((method, path, kwargs.get("json")))
            return {"id": 123}

    adapter = ShopWareAppointmentAdapter(live_settings(), FakeClient())

    adapter.update("123", {"start_time": "2026-07-10T17:00:00Z"})
    adapter.cancel("123")

    assert calls[0] == (
        "PUT",
        "/api/v1/tenants/99/appointments/123",
        {"shop_id": 7, "staff_id": 3, "start_at": "2026-07-10T17:00:00Z"},
    )
    assert calls[1] == ("DELETE", "/api/v1/tenants/99/appointments/123", None)

