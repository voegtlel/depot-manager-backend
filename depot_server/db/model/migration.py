from pydantic import Field
from pymongo import IndexModel, ASCENDING
from typing import Optional
from uuid import UUID

from depot_server.db.model.base import BaseDocument


class DbMigration(BaseDocument):
    __collection_name__ = 'migration'
    __indexes__ = []

    id: int = Field(..., alias='_id')
    epoch: int = Field(...)
    lock: Optional[bool] = Field(None)