import logging
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import configure_log_record_factory, get_logger, get_request_id
from app.core.metrics import (
    record_cache_hit,
    record_cache_miss,
    record_database_call,
    record_retry,
    record_shopware_call,
)
from app.core.middleware import request_observability_middleware


def make_test_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(request_observability_middleware)

    @app.get("/ok")
    def ok():
        get_logger("tests.observability").info("Route Log", extra={"route_marker": "ok"})
        return {"request_id": get_request_id()}

    @app.get("/error")
    def error():
        raise RuntimeError("boom")

    @app.get("/metrics")
    def metrics():
        record_shopware_call(12.25)
        record_shopware_call(7.75)
        record_database_call(3.5)
        record_retry()
        record_cache_hit()
        record_cache_miss()
        return {"ok": True}

    return app


def test_request_id_header_and_log_propagation(caplog):
    configure_log_record_factory()
    caplog.set_level(logging.INFO)
    client = TestClient(make_test_app())

    response = client.get("/ok")

    request_id = response.headers["X-Request-ID"]
    UUID(request_id)
    assert response.json()["request_id"] == request_id

    route_records = [record for record in caplog.records if record.getMessage() == "Route Log"]
    assert len(route_records) == 1
    assert route_records[0].request_id == request_id

    completed_records = [record for record in caplog.records if record.getMessage() == "Request Completed"]
    assert len(completed_records) == 1
    assert completed_records[0].request_id == request_id
    assert completed_records[0].http_method == "GET"
    assert completed_records[0].path == "/ok"
    assert completed_records[0].status_code == 200
    assert isinstance(completed_records[0].duration_ms, float)


def test_unhandled_exception_is_logged_with_request_id_and_stack_trace(caplog):
    configure_log_record_factory()
    caplog.set_level(logging.INFO)
    client = TestClient(make_test_app())

    response = client.get("/error")

    request_id = response.headers["X-Request-ID"]
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}

    exception_records = [record for record in caplog.records if record.getMessage() == "Unhandled Exception"]
    assert len(exception_records) == 1
    assert exception_records[0].request_id == request_id
    assert exception_records[0].status_code == 500
    assert exception_records[0].path == "/error"
    assert exception_records[0].exc_info is not None


def test_request_summary_includes_performance_metrics(caplog):
    configure_log_record_factory()
    caplog.set_level(logging.INFO)
    client = TestClient(make_test_app())

    response = client.get("/metrics")

    request_id = response.headers["X-Request-ID"]
    summary_records = [record for record in caplog.records if record.getMessage() == "Request Summary"]
    assert len(summary_records) == 1
    summary = summary_records[0]
    assert summary.request_id == request_id
    assert summary.status == "success"
    assert isinstance(summary.duration_ms, float)
    assert summary.shopware_calls == 2
    assert summary.shopware_time_ms == 20.0
    assert summary.database_calls == 1
    assert summary.database_time_ms == 3.5
    assert summary.retry_count == 1
    assert summary.error_count == 0
    assert summary.cache_hits == 1
    assert summary.cache_misses == 1
