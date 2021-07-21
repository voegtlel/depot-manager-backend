from .base import BaseModel


class User(BaseModel):
    sub: str
    name: str
    email: str
    picture: str
    phone_number: str
