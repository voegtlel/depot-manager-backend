from datetime import date
from pydantic import Field
from pymongo import IndexModel, ASCENDING
from typing import List, Optional
from uuid import UUID

from depot_server.db.model.base import BaseDocument
from depot_server.model import ItemCondition, TotalReportState


class DbItem(BaseDocument):
    __collection_name__ = 'item'
    __indexes__ = [IndexModel([('external_id', ASCENDING)])]

    id: UUID = Field(..., alias='_id')
    external_id: Optional[str] = None

    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    manufacture_date: Optional[date] = None
    purchase_date: Optional[date] = None
    first_use_date: Optional[date] = None

    name: str = Field(...)
    description: Optional[str] = None

    report_profile_id: Optional[UUID] = None

    total_report_state: Optional[TotalReportState] = TotalReportState.Fit
    condition: ItemCondition = ItemCondition.New
    condition_comment: Optional[str] = None

    last_service: Optional[date] = None

    picture_id: Optional[str] = None

    group_id: Optional[str] = None

    tags: List[str] = []

    bay_id: Optional[UUID] = None

    # Id of the reservation which currently has the item taken
    reservation_id: Optional[UUID] = None
