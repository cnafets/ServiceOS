import contextvars
from dataclasses import dataclass
from typing import Any


@dataclass
class RequestMetrics:
    shopware_calls: int = 0
    shopware_time_ms: float = 0.0
    database_calls: int = 0
    database_time_ms: float = 0.0
    retry_count: int = 0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    def summary(self, duration_ms: float, status: str) -> dict[str, Any]:
        return {
            "duration_ms": duration_ms,
            "shopware_calls": self.shopware_calls,
            "shopware_time_ms": round(self.shopware_time_ms, 2),
            "database_calls": self.database_calls,
            "database_time_ms": round(self.database_time_ms, 2),
            "retry_count": self.retry_count,
            "error_count": self.error_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "status": status,
        }


metrics_context: contextvars.ContextVar[RequestMetrics | None] = contextvars.ContextVar(
    "request_metrics",
    default=None,
)


def start_request_metrics() -> contextvars.Token[RequestMetrics | None]:
    return metrics_context.set(RequestMetrics())


def reset_request_metrics(token: contextvars.Token[RequestMetrics | None]) -> None:
    metrics_context.reset(token)


def get_request_metrics() -> RequestMetrics | None:
    return metrics_context.get()


def record_shopware_call(duration_ms: float, *, error: bool = False) -> None:
    metrics = get_request_metrics()
    if metrics is None:
        return
    metrics.shopware_calls += 1
    metrics.shopware_time_ms += duration_ms
    if error:
        metrics.error_count += 1


def record_database_call(duration_ms: float, *, error: bool = False) -> None:
    metrics = get_request_metrics()
    if metrics is None:
        return
    metrics.database_calls += 1
    metrics.database_time_ms += duration_ms
    if error:
        metrics.error_count += 1


def record_retry() -> None:
    metrics = get_request_metrics()
    if metrics is not None:
        metrics.retry_count += 1


def record_error() -> None:
    metrics = get_request_metrics()
    if metrics is not None:
        metrics.error_count += 1


def record_cache_hit() -> None:
    metrics = get_request_metrics()
    if metrics is not None:
        metrics.cache_hits += 1


def record_cache_miss() -> None:
    metrics = get_request_metrics()
    if metrics is not None:
        metrics.cache_misses += 1
