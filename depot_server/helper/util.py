import asyncio
import pytz
from datetime import datetime
from typing import Any


def utc_now() -> datetime:
    now = datetime.utcnow()
    return now.replace(tzinfo=pytz.UTC, microsecond=now.microsecond // 1000 * 1000)


def set_loop_attr(key: str, data: Any) -> None:
    setattr(asyncio.get_running_loop(), f"_{key}", data)


def get_loop_attr(key: str) -> Any:
    return getattr(asyncio.get_running_loop(), f"_{key}", None)
