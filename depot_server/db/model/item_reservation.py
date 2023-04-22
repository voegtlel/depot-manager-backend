from datetime import date
from pydantic import Field
from pymongo import IndexModel, ASCENDING, DESCENDING
from uuid import UUID

from depot_server.db.model.base import BaseDocument
from depot_server.model import ReservationState


class DbItemReservation(BaseDocument):
    __collection_name__ = 'itemReservation'
    __indexes__ = [
        IndexModel([('start', ASCENDING), ('item_id', ASCENDING)]),
        IndexModel([('end', DESCENDING), ('item_id', ASCENDING)]),
        IndexModel([('item_id', ASCENDING), ('start', ASCENDING), ('item_id', ASCENDING)]),
        IndexModel([('item_id', ASCENDING), ('end', DESCENDING), ('item_id', ASCENDING)]),
        IndexModel([('reservation_id', ASCENDING), ('start', ASCENDING), ('item_id', ASCENDING)]),
        IndexModel([('reservation_id', ASCENDING), ('end', DESCENDING), ('item_id', ASCENDING)]),
    ]

    id: UUID = Field(..., alias='_id')
    reservation_id: UUID = Field(...)
    item_id: UUID = Field(...)

    # State of the item
    state: ReservationState = Field(...)

    # Store this individually, such that every item can be returned earlier, etc.
    start: date = Field(...)
    end: date = Field(...)
