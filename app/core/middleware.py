import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.responses import Response

from app.core.logging import get_logger, reset_request_id, set_request_id
from app.core.metrics import get_request_metrics, record_error, reset_request_metrics, start_request_metrics

logger = get_logger(__name__)


async def request_observability_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request_id = str(uuid4())
    request_id_token = set_request_id(request_id)
    metrics_token = start_request_metrics()
    start = time.perf_counter()
    method = request.method
    path = request.url.path

    logger.info("Request Started", extra={"http_method": method, "path": path})
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        record_error()
        logger.exception(
            "Unhandled Exception",
            extra={"http_method": method, "path": path, "status_code": 500, "duration_ms": duration_ms},
        )
        response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
        response.headers["X-Request-ID"] = request_id
        _log_request_summary(duration_ms, "error")
        reset_request_metrics(metrics_token)
        reset_request_id(request_id_token)
        return response

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    status = "success" if response.status_code < 400 else "error"
    if status == "error":
        record_error()
    logger.info(
        "Request Completed",
        extra={
            "http_method": method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    _log_request_summary(duration_ms, status)
    reset_request_metrics(metrics_token)
    reset_request_id(request_id_token)
    return response


def _log_request_summary(duration_ms: float, status: str) -> None:
    metrics = get_request_metrics()
    summary = metrics.summary(duration_ms, status) if metrics is not None else {"duration_ms": duration_ms, "status": status}
    logger.info("Request Summary", extra=summary)
