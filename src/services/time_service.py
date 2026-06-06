from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC = timezone.utc


def app_timezone():
    timezone_name = os.getenv("APP_TIMEZONE") or os.getenv("TZ") or "Asia/Bangkok"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name == "Asia/Bangkok":
            return timezone(timedelta(hours=7), name="Asia/Bangkok")
        return UTC


def timezone_name(value=None) -> str:
    tz = value or app_timezone()
    return getattr(tz, "key", None) or tz.tzname(None) or "UTC"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def to_app_datetime(value: datetime | None = None) -> datetime:
    source = value or utc_now()
    if source.tzinfo is None:
        source = source.replace(tzinfo=UTC)
    return source.astimezone(app_timezone())


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def local_day_start_utc(day: date | None = None) -> datetime:
    tz = app_timezone()
    local_day = day or datetime.now(tz).date()
    local_start = datetime.combine(local_day, time.min, tzinfo=tz)
    return local_start.astimezone(UTC).replace(tzinfo=None)
