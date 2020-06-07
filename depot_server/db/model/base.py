from enum import Enum

from datetime import datetime, date
from pydantic import BaseModel
from pymongo import IndexModel
from typing import List, Any, Sequence, Mapping, TypeVar, Type
from uuid import UUID


def _safe_document(doc: Any):
    if doc is None or isinstance(doc, (str, int, float, bool, UUID, datetime)):
        return doc
    if isinstance(doc, Enum):
        return doc.value
    if isinstance(doc, Mapping):
        return {k: _safe_document(v) for k, v in doc.items()}
    if isinstance(doc, Sequence):
        return [_safe_document(x) for x in doc]
    if isinstance(doc, date):
        return doc.toordinal()
    raise ValueError(f"Invalid document: {doc}")


def _validate_document(doc: Any, type_: type) -> Any:
    if doc is None:
        return doc
    if issubclass(type_, BaseSubDocument):
        assert isinstance(doc, dict)
        return {
            key: _validate_document(doc.get(field.alias if field.has_alias else key), field.type_)
            for key, field in type_.__fields__.items()
        }
    if issubclass(type_, date) and isinstance(doc, (int, float)):
        return date.fromordinal(int(doc))
    return doc


TDocument = TypeVar('TDocument', bound='BaseSubDocument')


class BaseSubDocument(BaseModel):
    class Config:
        allow_population_by_field_name = True
        validate_assignment = True


class BaseDocument(BaseSubDocument):
    __indexes__: List[IndexModel] = []
    __collection_name__: str

    def document(self):
        return _safe_document(self.dict(exclude_none=True, by_alias=True))

    @classmethod
    def validate_document(cls: Type[TDocument], doc: dict) -> TDocument:
        assert isinstance(doc, dict)
        return cls.validate(_validate_document(doc, cls))

    def update_from(self, src_doc):
        if isinstance(src_doc, BaseModel):
            for key in src_doc.__fields__.keys():
                if key in self.__fields__:
                    setattr(self, key, getattr(src_doc, key))
