import httpx

from app.core.config import Settings
from app.core.metrics import get_request_metrics, reset_request_metrics, start_request_metrics
from app.integrations.shopware.adapter import (
    ShopWareAppointmentAdapter,
    ShopWareCustomerAdapter,
    ShopWareRepairOrderAdapter,
    ShopWareVehicleAdapter,
)
from app.integrations.shopware.client import ShopWareClient
from app.schemas.shopware import (
    ShopWareCustomerCreate,
    ShopWareCustomerUpdate,
    ShopWareRepairOrderCreate,
    ShopWareRepairOrderUpdate,
    ShopWareVehicleCreate,
    ShopWareVehicleUpdate,
)


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


def test_shopware_client_records_metrics_for_retry_and_latency():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, json={"error": "temporary"})
        return httpx.Response(200, json={"ok": True})

    settings = live_settings()
    settings.shopware_retry_attempts = 2
    settings.shopware_retry_backoff_seconds = 0
    client = ShopWareClient(settings, transport=httpx.MockTransport(handler))
    token = start_request_metrics()
    try:
        response = client.request("GET", "/api/v1/tenants")
        metrics = get_request_metrics()
    finally:
        reset_request_metrics(token)

    assert response == {"ok": True}
    assert metrics is not None
    assert metrics.shopware_calls == 2
    assert metrics.shopware_time_ms >= 0
    assert metrics.retry_count == 1
    assert metrics.error_count == 1


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


def test_appointment_adapter_retrieves_appointment():
    calls = []

    class FakeClient:
        def request(self, method, path, **kwargs):
            calls.append((method, path))
            return {"id": 123}

    adapter = ShopWareAppointmentAdapter(live_settings(), FakeClient())

    result = adapter.retrieve("123")

    assert result == {"id": 123}
    assert calls == [("GET", "/api/v1/tenants/99/appointments/123")]


def test_appointment_adapter_integration_test_mode_returns_mock_id():
    settings = live_settings()
    settings.integration_test_mode = True

    class FailingClient:
        def request(self, method, path, **kwargs):
            raise AssertionError("Integration test mode should not call live Shop-Ware.")

    adapter = ShopWareAppointmentAdapter(settings, FailingClient())

    result = adapter.create(7, {"start_time": "2026-07-10T14:00:00Z"})

    assert result.success is True
    assert result.remote_id == "mock-sw-7"


def test_customer_adapter_uses_official_create_endpoint_and_payload():
    captured = {}

    class FakeClient:
        def request(self, method, path, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["json"] = kwargs["json"]
            return {"id": 42, "first_name": "Jane", "last_name": "Driver", "shop_ids": [7]}

    adapter = ShopWareCustomerAdapter(live_settings(), FakeClient())
    result = adapter.create(
        ShopWareCustomerCreate(
            first_name="Jane",
            last_name="Driver",
            email="jane@example.com",
            phones=[{"number": "+15550100", "preferred": True, "show_on_ro": True}],
        )
    )

    assert result["id"] == 42
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/tenants/99/customers"
    assert captured["json"]["shop_id"] == 7
    assert captured["json"]["first_name"] == "Jane"
    assert captured["json"]["phones"][0]["number"] == "+15550100"


def test_customer_adapter_searches_with_official_filters():
    captured = {}

    class FakeClient:
        def request(self, method, path, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["params"] = kwargs["params"]
            return {"results": [{"id": 42, "last_name": "Driver"}], "total_count": 1}

    adapter = ShopWareCustomerAdapter(live_settings(), FakeClient())
    result = adapter.search("Driver", page=2, per_page=10)

    assert result["total_count"] == 1
    assert captured["method"] == "GET"
    assert captured["path"] == "/api/v1/tenants/99/customers"
    assert captured["params"] == {"page": 2, "per_page": 10, "last_name": "Driver"}


def test_customer_adapter_retrieves_and_updates_customer():
    calls = []

    class FakeClient:
        def request(self, method, path, **kwargs):
            calls.append((method, path, kwargs.get("json")))
            return {"id": 42, "first_name": "Janet"}

    adapter = ShopWareCustomerAdapter(live_settings(), FakeClient())
    retrieved = adapter.retrieve(42)
    updated = adapter.update(42, ShopWareCustomerUpdate(first_name="Janet"))

    assert retrieved["id"] == 42
    assert updated["first_name"] == "Janet"
    assert calls[0] == ("GET", "/api/v1/tenants/99/customers/42", None)
    assert calls[1] == ("PUT", "/api/v1/tenants/99/customers/42", {"first_name": "Janet"})


def test_customer_adapter_mock_mode_does_not_call_shopware():
    settings = live_settings()
    settings.integration_test_mode = True

    class FailingClient:
        def request(self, method, path, **kwargs):
            raise AssertionError("Mock mode should not call live Shop-Ware.")

    adapter = ShopWareCustomerAdapter(settings, FailingClient())

    assert adapter.search("Driver") == {"results": [], "mode": "mock"}
    assert adapter.retrieve(42) == {"id": 42, "mode": "mock"}
    assert adapter.create(ShopWareCustomerCreate(first_name="Jane"))["mode"] == "mock"


def test_vehicle_adapter_uses_official_create_endpoint_and_payload():
    captured = {}

    class FakeClient:
        def request(self, method, path, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["json"] = kwargs["json"]
            return {"id": 21, "make": "Ford", "model": "Expedition", "customer_ids": [42]}

    adapter = ShopWareVehicleAdapter(live_settings(), FakeClient())
    result = adapter.create(
        ShopWareVehicleCreate(
            vin="1FMPU16W14LB56648",
            year="2004",
            make="Ford",
            model="Expedition",
            engine="4.6L V8",
            customer_ids=[42],
        )
    )

    assert result["id"] == 21
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/tenants/99/vehicles"
    assert captured["json"]["vin"] == "1FMPU16W14LB56648"
    assert captured["json"]["make"] == "Ford"
    assert captured["json"]["customer_ids"] == [42]


def test_vehicle_adapter_searches_by_vin_and_customer_id():
    calls = []

    class FakeClient:
        def request(self, method, path, **kwargs):
            calls.append((method, path, kwargs["params"]))
            return {"results": [{"id": 21, "vin": "1FMPU16W14LB56648"}], "total_count": 1}

    adapter = ShopWareVehicleAdapter(live_settings(), FakeClient())
    vin_result = adapter.lookup_by_vin("1FMPU16W14LB56648", page=2, per_page=10)
    customer_result = adapter.search_by_customer(42)

    assert vin_result["total_count"] == 1
    assert customer_result["total_count"] == 1
    assert calls[0] == (
        "GET",
        "/api/v1/tenants/99/vehicles",
        {"page": 2, "per_page": 10, "vin": "1FMPU16W14LB56648"},
    )
    assert calls[1] == (
        "GET",
        "/api/v1/tenants/99/vehicles",
        {"page": 1, "per_page": 30, "customer_id": 42},
    )


def test_vehicle_adapter_retrieves_and_updates_vehicle():
    calls = []

    class FakeClient:
        def request(self, method, path, **kwargs):
            calls.append((method, path, kwargs.get("json")))
            return {"id": 21, "make": "Ford", "color": "Black"}

    adapter = ShopWareVehicleAdapter(live_settings(), FakeClient())
    retrieved = adapter.retrieve(21)
    updated = adapter.update(21, ShopWareVehicleUpdate(color="Black", customer_ids=[42]))

    assert retrieved["id"] == 21
    assert updated["color"] == "Black"
    assert calls[0] == ("GET", "/api/v1/tenants/99/vehicles/21", None)
    assert calls[1] == ("PUT", "/api/v1/tenants/99/vehicles/21", {"color": "Black", "customer_ids": [42]})


def test_vehicle_adapter_mock_mode_does_not_call_shopware():
    settings = live_settings()
    settings.integration_test_mode = True

    class FailingClient:
        def request(self, method, path, **kwargs):
            raise AssertionError("Mock mode should not call live Shop-Ware.")

    adapter = ShopWareVehicleAdapter(settings, FailingClient())

    assert adapter.search(vin="1FMPU16W14LB56648") == {"results": [], "mode": "mock"}
    assert adapter.retrieve(21) == {"id": 21, "mode": "mock"}
    assert adapter.create(ShopWareVehicleCreate(make="Ford"))["mode"] == "mock"
    assert adapter.update(21, ShopWareVehicleUpdate(model="Expedition"))["mode"] == "mock"


def test_repair_order_adapter_uses_official_create_endpoint_and_payload():
    captured = {}

    class FakeClient:
        def request(self, method, path, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["json"] = kwargs["json"]
            return {"id": 77, "customer_id": 42, "vehicle_id": 21, "shop_id": 7}

    adapter = ShopWareRepairOrderAdapter(live_settings(), FakeClient())
    result = adapter.create(
        ShopWareRepairOrderCreate(
            customer_id=42,
            vehicle_id=21,
            shop_id=7,
            customer_concern="No-start diagnostic",
            preferred_contact_type="text",
        )
    )

    assert result["id"] == 77
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/tenants/99/repair_orders"
    assert captured["json"]["customer_id"] == 42
    assert captured["json"]["vehicle_id"] == 21
    assert captured["json"]["shop_id"] == 7
    assert captured["json"]["customer_concern"] == "No-start diagnostic"


def test_repair_order_adapter_searches_with_official_filters():
    captured = {}

    class FakeClient:
        def request(self, method, path, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["params"] = kwargs["params"]
            return {"results": [{"id": 77, "state": "estimate"}], "total_count": 1}

    adapter = ShopWareRepairOrderAdapter(live_settings(), FakeClient())
    result = adapter.search(customer_id=42, vehicle_id=21, status="estimate", page=2, per_page=10)

    assert result["total_count"] == 1
    assert captured["method"] == "GET"
    assert captured["path"] == "/api/v1/tenants/99/repair_orders"
    assert captured["params"] == {
        "page": 2,
        "per_page": 10,
        "customer_id": 42,
        "vehicle_id": 21,
        "status": "estimate",
    }


def test_repair_order_adapter_retrieves_and_updates_repair_order():
    calls = []

    class FakeClient:
        def request(self, method, path, **kwargs):
            calls.append((method, path, kwargs.get("json"), kwargs.get("params")))
            return {"id": 77, "customer_concern": "Updated concern"}

    adapter = ShopWareRepairOrderAdapter(live_settings(), FakeClient())
    retrieved = adapter.retrieve(77)
    updated = adapter.update(77, ShopWareRepairOrderUpdate(customer_concern="Updated concern"))

    assert retrieved["id"] == 77
    assert updated["customer_concern"] == "Updated concern"
    assert calls[0] == ("GET", "/api/v1/tenants/99/repair_orders/77", None, None)
    assert calls[1] == (
        "PUT",
        "/api/v1/tenants/99/repair_orders/77",
        {"customer_concern": "Updated concern"},
        None,
    )


def test_repair_order_adapter_mock_mode_does_not_call_shopware():
    settings = live_settings()
    settings.integration_test_mode = True

    class FailingClient:
        def request(self, method, path, **kwargs):
            raise AssertionError("Mock mode should not call live Shop-Ware.")

    adapter = ShopWareRepairOrderAdapter(settings, FailingClient())

    assert adapter.search(customer_id=42) == {"results": [], "mode": "mock"}
    assert adapter.retrieve(77) == {"id": 77, "mode": "mock"}
    assert adapter.create(ShopWareRepairOrderCreate(customer_id=42, shop_id=7))["mode"] == "mock"
    assert adapter.update(77, ShopWareRepairOrderUpdate(detail="Updated"))["mode"] == "mock"
