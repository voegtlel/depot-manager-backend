from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import Field
from pymongo import IndexModel, ASCENDING

from depot_server.db.model.base import BaseDocument
from depot_server.model import ReservationType


class DbReservation(BaseDocument):
    __collection_name__ = 'reservation'
    __indexes__ = [
        IndexModel([('end', ASCENDING), ('start', ASCENDING)]),
        IndexModel([('items', ASCENDING), ('end', ASCENDING), ('start', ASCENDING)]),
        IndexModel([('user_id', ASCENDING), ('end', ASCENDING), ('start', ASCENDING)]),
        IndexModel([('user_id', ASCENDING), ('items', ASCENDING), ('end', ASCENDING), ('start', ASCENDING)]),
    ]

    id: UUID = Field(..., alias='_id')
    type: ReservationType = Field(...)
    name: str = Field(...)

    start: date = Field(...)
    end: date = Field(...)

    user_id: str = Field(...)
    team_id: Optional[str] = None

    contact: str = Field(...)

    items: List[UUID] = Field(...)

    returned: bool = Field(False)
