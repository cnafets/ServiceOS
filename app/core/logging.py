import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

_BASE_LOG_RECORD_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())
_LOG_RECORD_FACTORY_CONFIGURED = False


def get_request_id() -> str | None:
    return request_id_context.get()


def set_request_id(request_id: str) -> contextvars.Token[str | None]:
    return request_id_context.set(request_id)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    request_id_context.reset(token)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }

        for key, value in record.__dict__.items():
            if key not in _BASE_LOG_RECORD_KEYS and key not in {"request_id", "message", "asctime"}:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None) or "-"
        record.request_id = request_id
        return super().format(record)


def configure_logging(level: str, log_format: str = "text") -> None:
    configure_log_record_factory()

    handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            TextFormatter("%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s")
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def configure_log_record_factory() -> None:
    global _LOG_RECORD_FACTORY_CONFIGURED
    if _LOG_RECORD_FACTORY_CONFIGURED:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous_factory(*args, **kwargs)
        record.request_id = get_request_id()
        return record

    logging.setLogRecordFactory(record_factory)
    _LOG_RECORD_FACTORY_CONFIGURED = True
