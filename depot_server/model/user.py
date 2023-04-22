from typing import Optional, List

from .base import BaseModel


class User(BaseModel):
    sub: str
    name: str
    email: str
    picture: Optional[str]
    phone_number: Optional[str]
    roles: Optional[List[str]]
    teams: Optional[List[str]]
