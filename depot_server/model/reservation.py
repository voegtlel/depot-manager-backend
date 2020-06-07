from enum import Enum

from datetime import date
from pydantic import Field
from typing import List, Optional
from uuid import UUID

from .base import BaseModel


class ReservationType(str, Enum):
    PRIVATE = 'private'
    TEAM = 'team'


class Reservation(BaseModel):
    id: UUID = Field(...)
    type: ReservationType = Field(...)
    name: str = Field(...)

    start: date = Field(...)
    end: date = Field(...)

    user_id: str = Field(...)
    team_id: Optional[str] = None

    contact: str = Field(...)

    items: List[UUID] = Field(...)


class ReservationInWrite(BaseModel):
    type: ReservationType = Field(...)
    name: str = Field(...)

    start: date = Field(...)
    end: date = Field(...)

    user_id: Optional[str] = None
    team_id: Optional[str] = None

    contact: str = Field(...)

    items: List[UUID] = Field(...)
