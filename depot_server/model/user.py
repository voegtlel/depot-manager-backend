from typing import Optional

from .base import BaseModel


class User(BaseModel):
    sub: str
    name: str
    email: str
    picture: Optional[str]
    phone_number: Optional[str]
