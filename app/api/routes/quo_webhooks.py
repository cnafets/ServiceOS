"""Receive Quo events securely. No customer actions are performed in this phase."""
import base64
import binascii
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.quo_webhook_event import QuoWebhookEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(body: bytes, headers, secret: str, now: int | None = None) -> bool:
    """Verify Quo's current (2026-03-30) Standard Webhooks signature."""
    webhook_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signatures = headers.get("webhook-signature", "")
    if not (webhook_id and timestamp and signatures and secret.startswith("whsec_")):
        return False
    try:
        issued = int(timestamp)
        if abs((int(time.time()) if now is None else now) - issued) > 300:
            return False
        key = base64.b64decode(secret[6:], validate=True)
        if not key:
            return False
        signed = f"{webhook_id}.{timestamp}.".encode() + body
        digest = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
        return any(
            hmac.compare_digest(token[3:], digest)
            for token in signatures.split()
            if token.startswith("v1,")
        )
    except (ValueError, binascii.Error):
        return False


@router.post("/quo")
async def receive_quo_webhook(request: Request, db: Session = Depends(get_db)):
    secret = os.environ.get("QUO_WEBHOOK_SIGNING_SECRET", "")
    raw = await request.body()
    if len(raw) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")
    if not verify_signature(raw, request.headers, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        event = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(event, dict) or not isinstance(event.get("type"), str) or not isinstance(event.get("id"), str):
        raise HTTPException(status_code=422, detail="Invalid event envelope")
    if len(event['id']) > 128 or len(event['type']) > 100:
        raise HTTPException(status_code=422, detail='Event fields too long')
    db.add(QuoWebhookEvent(event_id=event['id'], event_type=event['type'], payload=raw.decode('utf-8'), status='pending'))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    # Deliberately no customer replies, estimates, bookings or sensitive payload logs.
    # Next phase: durable event inbox + idempotent worker + human-takeover checks.
    return {"received": True, "event_id": event["id"], "processing": "disabled"}
