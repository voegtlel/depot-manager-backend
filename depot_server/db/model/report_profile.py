from typing import Optional, List
from uuid import UUID

from pydantic import Field
from pymongo import IndexModel, ASCENDING

from depot_server.db.model.base import BaseDocument


class DbReportProfile(BaseDocument):
    __collection_name__ = 'reportProfile'
    __indexes__ = []

    id: UUID = Field(..., alias='_id')
    title: str = Field(...)
    description: str = Field(...)
    elements: List[UUID] = Field(...)
