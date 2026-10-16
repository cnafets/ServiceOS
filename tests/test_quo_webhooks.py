import base64
import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from app.api.routes.quo_webhooks import verify_signature
from app.main import app

SECRET = "whsec_" + base64.b64encode(b"test-key").decode()


def signed_headers(body: bytes, timestamp: int, event_id: str = "evt_1"):
    message = f"{event_id}.{timestamp}.".encode() + body
    digest = base64.b64encode(hmac.new(b"test-key", message, hashlib.sha256).digest()).decode()
    return {
        "webhook-id": event_id,
        "webhook-timestamp": str(timestamp),
        "webhook-signature": f"v1,{digest}",
    }


def test_valid_signature():
    body = b'{"id":"evt_1","type":"message.received"}'
    assert verify_signature(body, signed_headers(body, 1000), SECRET, now=1000)


def test_rejects_modified_payload():
    body = b'{"id":"evt_1","type":"message.received"}'
    assert not verify_signature(body + b" ", signed_headers(body, 1000), SECRET, now=1000)


def test_rejects_old_timestamp():
    body = b"{}"
    assert not verify_signature(body, signed_headers(body, 1000), SECRET, now=1301)


def test_missing_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("QUO_WEBHOOK_SIGNING_SECRET", raising=False)
    with TestClient(app) as client:
        response = client.post("/api/v1/webhooks/quo", json={"id": "evt_1", "type": "message.received"})
    assert response.status_code == 401


def test_signed_event_acknowledged_without_processing(monkeypatch):
    monkeypatch.setenv("QUO_WEBHOOK_SIGNING_SECRET", SECRET)
    body = json.dumps({"id": "evt_1", "type": "message.received"}).encode()
    with TestClient(app) as client:
        response = client.post("/api/v1/webhooks/quo", content=body, headers=signed_headers(body, int(time.time())))
    assert response.status_code == 200
    assert response.json() == {"received": True, "event_id": "evt_1", "processing": "disabled"}
