from enum import Enum

from pydantic import Field
from uuid import UUID

from .base import BaseModel


class ReportState(Enum):
    NotApplicable = 'not-applicable'
    Good = 'good'
    Monitor = 'monitor'
    Repair = 'repair'
    Retire = 'retire'


class ReportElement(BaseModel):
    id: UUID = Field(...)
    title: str = Field(...)
    description: str = Field(...)


class ReportElementInWrite(BaseModel):
    title: str = Field(...)
    description: str = Field(...)
