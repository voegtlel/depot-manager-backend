from datetime import date
from enum import IntEnum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReservationType(IntEnum):
    PRIVATE = 1
    TEAM = 2


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
