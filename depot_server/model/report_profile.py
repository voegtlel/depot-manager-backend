from enum import Enum

from pydantic import Field
from typing import List
from uuid import UUID

from .base import BaseModel


class TotalReportState(Enum):
    Fit = 'fit'
    Unfit = 'unfit'


class ReportProfile(BaseModel):
    id: UUID = Field(...)
    name: str = Field(...)
    description: str = Field(...)
    elements: List[UUID] = Field(...)


class ReportProfileInWrite(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    elements: List[UUID] = Field(...)
