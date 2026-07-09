from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def ensure_timezone(value: datetime, timezone_name: str) -> datetime:
    if value.tzinfo is not None and value.utcoffset() is not None:
        return value
    return value.replace(tzinfo=ZoneInfo(timezone_name))


def rfc3339_datetime(value: datetime, timezone_name: str, *, use_utc_z: bool = True) -> str:
    aware = ensure_timezone(value, timezone_name)
    if use_utc_z:
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return aware.isoformat()


def rfc3339_datetime_value(value: datetime | str | None, timezone_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return rfc3339_datetime(value, timezone_name)

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return rfc3339_datetime(parsed, timezone_name)
