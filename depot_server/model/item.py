from datetime import date
from pydantic import Field
from typing import List, Optional
from uuid import UUID

from .base import BaseModel
from .item_state import ItemReport, ItemCondition
from .report_profile import TotalReportState


class Item(BaseModel):
    id: UUID = Field(...)
    external_id: Optional[str] = None
    name: str = Field(...)
    description: Optional[str] = None

    report_profile_id: Optional[UUID] = None

    total_report_state: TotalReportState = Field(...)
    condition: ItemCondition = Field(...)
    condition_comment: Optional[str] = None

    purchase_date: Optional[date] = None
    last_service: Optional[date] = None

    picture_id: Optional[str] = None

    group_id: Optional[str] = None

    tags: List[str] = []

    bay_id: Optional[UUID] = None


class ItemInWrite(BaseModel):
    external_id: Optional[str] = None
    name: str = Field(...)
    description: Optional[str] = None

    report_profile_id: Optional[UUID] = None

    condition: ItemCondition = Field(...)
    condition_comment: Optional[str] = None

    purchase_date: Optional[date] = None

    picture_id: Optional[str] = None

    group_id: Optional[str] = None

    tags: List[str] = []

    bay_id: Optional[UUID] = None

    change_comment: str = Field(...)


class ReportItemInWrite(ItemInWrite):
    last_service: Optional[date] = None

    total_report_state: TotalReportState = Field(...)
    report: List[ItemReport]
