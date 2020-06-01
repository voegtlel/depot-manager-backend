from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Bay(BaseModel):
    id: UUID = Field(...)
    external_id: Optional[str] = None
    name: str = Field(...)
    description: Optional[str] = None


class BayInWrite(BaseModel):
    external_id: Optional[str] = None
    name: str = Field(...)
    description: Optional[str] = None
