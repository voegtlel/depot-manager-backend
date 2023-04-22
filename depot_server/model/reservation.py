from enum import Enum

from datetime import date
from pydantic import Field
from typing import List, Optional
from uuid import UUID

from .base import BaseModel


class ReservationType(str, Enum):
    PRIVATE = 'private'
    TEAM = 'team'


class ReservationState(str, Enum):
    RESERVED = 'reserved'
    TAKEN = 'taken'
    RETURNED = 'returned'
    RETURN_PROBLEM = 'return-problem'


class ReservationItem(BaseModel):
    item_id: UUID = Field(...)
    state: ReservationState = Field(...)


class Reservation(BaseModel):
    id: UUID = Field(...)
    type: ReservationType = Field(...)
    code: Optional[str] = Field(None)
    state: ReservationState = Field(...)
    active: Optional[bool] = Field(None)
    name: str = Field(...)

    start: date = Field(...)
    end: date = Field(...)

    user_id: str = Field(...)
    team_id: Optional[str] = Field(None)

    contact: str = Field(...)

    items: Optional[List[ReservationItem]] = Field(None)


class ReservationInWrite(BaseModel):
    type: ReservationType = Field(...)
    name: str = Field(...)

    start: date = Field(...)
    end: date = Field(...)

    user_id: Optional[str] = Field(None)
    team_id: Optional[str] = Field(None)

    contact: str = Field(...)

    items: List[UUID] = Field(...)


class ReservationAction(str, Enum):
    Take = 'take'
    Return = 'return'
    Remove = 'remove'
    Broken = 'broken'
    Missing = 'missing'


class ReservationItemState(BaseModel):
    item_id: UUID
    action: ReservationAction
    comment: Optional[str] = None


class ReservationActionInWrite(BaseModel):
    items: List[ReservationItemState] = Field(...)

    comment: Optional[str] = None
