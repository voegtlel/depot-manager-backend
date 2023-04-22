from datetime import datetime

from .base import BaseModel


class Picture(BaseModel):
    id: str
    size: int
    original_name: str
    mime_type: str
    upload_timestamp: datetime
