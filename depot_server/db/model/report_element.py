from typing import Optional
from uuid import UUID

from pydantic import Field
from pymongo import IndexModel, ASCENDING

from depot_server.db.model.base import BaseDocument


class DbReportElement(BaseDocument):
    __collection_name__ = 'reportElement'
    __indexes__ = []

    id: UUID = Field(..., alias='_id')
    title: str = Field(...)
    description: str = Field(...)
