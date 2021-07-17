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

    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    manufacture_date: Optional[date] = None
    purchase_date: Optional[date] = None
    first_use_date: Optional[date] = None

    name: str = Field(...)
    description: Optional[str] = None

    report_profile_id: Optional[UUID] = None

    total_report_state: Optional[TotalReportState] = Field(...)
    condition: ItemCondition = Field(...)
    condition_comment: Optional[str] = None

    last_service: Optional[date] = None

    picture_id: Optional[str] = None

    group_id: Optional[str] = None

    tags: List[str] = []

    bay_id: Optional[UUID] = None


class ItemInWrite(BaseModel):
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

    condition: ItemCondition = Field(...)
    condition_comment: Optional[str] = None

    picture_id: Optional[str] = None

    group_id: Optional[str] = None

    tags: List[str] = []

    bay_id: Optional[UUID] = None

    change_comment: str = Field(...)


class ReportItemInWrite(ItemInWrite):
    last_service: Optional[date] = None

    total_report_state: TotalReportState = Field(...)
    report: List[ItemReport]
