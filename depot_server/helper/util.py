import pytz
from datetime import datetime


def utc_now() -> datetime:
    now = datetime.utcnow()
    return now.replace(tzinfo=pytz.UTC, microsecond=now.microsecond // 1000 * 1000)
