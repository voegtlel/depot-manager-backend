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
    name: str = Field(...)
    description: Optional[str] = None

    report_profile_id: Optional[UUID] = None

    total_report_state: TotalReportState = TotalReportState.Fit
    condition: ItemCondition = ItemCondition.New
    condition_comment: Optional[str] = None

    purchase_date: Optional[date] = None
    last_service: Optional[date] = None

    picture_id: Optional[str] = None

    group_id: Optional[str] = None

    tags: List[str] = []

    bay_id: Optional[UUID] = None
