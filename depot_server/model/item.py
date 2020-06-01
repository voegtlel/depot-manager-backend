import enum
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ItemCondition(str, enum.Enum):
    Good = 'good'
    Ok = 'ok'
    Bad = 'bad'
    Gone = 'gone'
    New = 'new'


class Item(BaseModel):
    id: UUID = Field(...)
    external_id: Optional[str] = None
    name: str = Field(...)
    description: Optional[str] = None

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

    condition: ItemCondition = Field(...)
    condition_comment: Optional[str] = None

    purchase_date: Optional[date] = None
    last_service: Optional[date] = None

    picture_id: Optional[str] = None

    group_id: Optional[str] = None

    tags: List[str] = []

    bay_id: Optional[UUID] = None

    change_comment: Optional[str] = None


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


class ItemConditionChange(BaseModel):
    previous: ItemCondition
    next: ItemCondition


class ItemStateChanges(BaseModel):
    external_id: Optional[StrChange] = None
    name: Optional[StrChange] = None
    description: Optional[StrChange] = None

    condition: Optional[ItemConditionChange] = None
    condition_comment: Optional[StrChange] = None

    purchase_date: Optional[DateChange] = None
    last_service: Optional[DateChange] = None

    picture_id: Optional[StrChange] = None

    group_id: Optional[StrChange] = None

    tags: Optional[TagsChange] = None

    bay_id: Optional[IdChange] = None

    change_comment: Optional[StrChange] = None


class ItemState(BaseModel):
    id: UUID = Field(...)
    item_id: UUID = Field(...)

    timestamp: datetime = Field(...)

    changes: ItemStateChanges = Field(...)

    user_id: str = Field(...)

    comment: str = Field(...)
