from pydantic import Field
from pymongo import IndexModel, ASCENDING
from typing import Optional
from uuid import UUID

from depot_server.db.model.base import BaseDocument


class DbBay(BaseDocument):
    __collection_name__ = 'bay'
    __indexes__ = [IndexModel([('external_id', ASCENDING)])]

    id: UUID = Field(..., alias='_id')
    external_id: Optional[str] = None
    name: str = Field(...)
    description: Optional[str] = None
