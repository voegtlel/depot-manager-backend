from pydantic import Field
from typing import List
from uuid import UUID

from depot_server.db.model.base import BaseDocument


class DbReportProfile(BaseDocument):
    __collection_name__ = 'reportProfile'
    __indexes__ = []

    id: UUID = Field(..., alias='_id')
    name: str = Field(...)
    description: str = Field(...)
    elements: List[UUID] = Field(...)
