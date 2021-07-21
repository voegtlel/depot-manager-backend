from datetime import datetime

import pytz


def utc_now() -> datetime:
    now = datetime.utcnow()
    micros = now.microsecond % 1000
    return now.replace(tzinfo=pytz.UTC, microsecond=now.microsecond - micros + (0 if micros < 500 else 1000))
