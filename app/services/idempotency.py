import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.idempotency import IdempotencyRecord
from app.schemas.intake import IntakeData, IntakeWorkflowResult

logger = get_logger(__name__)


class IdempotencyService:
    def __init__(self, db: Session, ttl_seconds: int) -> None:
        self.db = db
        self.ttl_seconds = ttl_seconds

    def get_completed_result(self, key: str, payload: IntakeData) -> IntakeWorkflowResult | None:
        record = self.db.get(IdempotencyRecord, key)
        if record is None:
            return None

        now = datetime.now(UTC)
        if self._is_expired(record, now):
            logger.info("Idempotency Record Expired", extra={"idempotency_key": key})
            self.db.delete(record)
            self.db.commit()
            return None

        request_hash = self.request_hash(payload)
        if record.request_hash != request_hash:
            raise ValueError("Idempotency key was already used with a different request payload.")

        logger.info("Idempotency Replay", extra={"idempotency_key": key})
        return IntakeWorkflowResult.model_validate_json(record.response_json)

    def store_completed_result(self, key: str, payload: IntakeData, result: IntakeWorkflowResult) -> None:
        now = datetime.now(UTC)
        record = IdempotencyRecord(
            key=key,
            request_hash=self.request_hash(payload),
            response_json=result.model_dump_json(),
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        self.db.merge(record)
        self.db.commit()
        logger.info("Idempotency Result Stored", extra={"idempotency_key": key})

    def request_hash(self, payload: IntakeData) -> str:
        payload_data: dict[str, Any] = payload.model_dump(mode="json", exclude={"idempotency_key"})
        canonical = json.dumps(payload_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _is_expired(self, record: IdempotencyRecord, now: datetime) -> bool:
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= now
