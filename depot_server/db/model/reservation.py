from datetime import date
from pydantic import Field
from pymongo import IndexModel, ASCENDING
from typing import Optional
from uuid import UUID

from depot_server.db.model.base import BaseDocument
from depot_server.model import ReservationType, ReservationState


class DbReservation(BaseDocument):
    __collection_name__ = 'reservation'
    __indexes__ = [
        # Used to list all reservations (including inactive)
        IndexModel([('end', ASCENDING), ('start', ASCENDING)], sparse=True),
        # Used to list only active reservations
        IndexModel([('active', ASCENDING), ('end', ASCENDING), ('start', ASCENDING)], sparse=True),
        # Used to find reservations for a specific item id
        IndexModel([('active', ASCENDING), ('user_id', ASCENDING), ('end', ASCENDING), ('start', ASCENDING)]),
        IndexModel([('code', ASCENDING)], sparse=True),
        IndexModel([('state', ASCENDING)]),
    ]

    id: UUID = Field(..., alias='_id')
    type: ReservationType = Field(...)
    code: Optional[str] = Field(None)
    state: ReservationState = Field(ReservationState.RESERVED)
    active: Optional[bool] = Field(True)
    name: str = Field(...)

    start: date = Field(...)
    end: date = Field(...)

    user_id: str = Field(...)
    team_id: Optional[str] = Field(None)

    contact: str = Field(...)
