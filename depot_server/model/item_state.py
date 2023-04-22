from enum import Enum

from datetime import date, datetime
from pydantic import Field
from typing import List, Optional
from uuid import UUID

from .base import BaseModel
from .report_element import ReportState
from .report_profile import TotalReportState


class ItemCondition(str, Enum):
    Good = 'good'
    Ok = 'ok'
    Bad = 'bad'
    Gone = 'gone'
    New = 'new'


class StrChange(BaseModel):
    previous: Optional[str]
    next: Optional[str]


class IdChange(BaseModel):
    previous: Optional[UUID]
    next: Optional[UUID]


class DateChange(BaseModel):
    previous: Optional[date]
    next: Optional[date]


class TagsChange(BaseModel):
    previous: List[str]
    next: List[str]


class TotalReportStateChange(BaseModel):
    previous: Optional[TotalReportState]
    next: Optional[TotalReportState]


class ItemConditionChange(BaseModel):
    previous: ItemCondition
    next: ItemCondition


class ItemStateChanges(BaseModel):
    external_id: Optional[StrChange] = None

    manufacturer: Optional[StrChange] = None
    model: Optional[StrChange] = None
    serial_number: Optional[StrChange] = None
    manufacture_date: Optional[DateChange] = None
    purchase_date: Optional[DateChange] = None
    first_use_date: Optional[DateChange] = None

    name: Optional[StrChange] = None
    description: Optional[StrChange] = None

    report_profile_id: Optional[IdChange] = None

    total_report_state: Optional[TotalReportStateChange] = None
    condition: Optional[ItemConditionChange] = None
    condition_comment: Optional[StrChange] = None

    last_service: Optional[DateChange] = None

    picture_id: Optional[StrChange] = None

    group_id: Optional[StrChange] = None

    tags: Optional[TagsChange] = None

    bay_id: Optional[IdChange] = None

    reservation_id: Optional[IdChange] = None


class ItemReport(BaseModel):
    report_element_id: UUID = Field(...)
    state: ReportState = Field(...)
    comment: Optional[str] = None


class ItemState(BaseModel):
    id: UUID = Field(...)
    item_id: UUID = Field(...)

    timestamp: datetime = Field(...)

    changes: ItemStateChanges = Field(...)
    report: Optional[List[ItemReport]] = None

    user_id: str = Field(...)

    comment: Optional[str] = Field(None)
