from enum import Enum

from datetime import datetime, date
from pydantic import BaseModel
from pymongo import IndexModel
from typing import List, Any, Sequence, Mapping, TypeVar, Type, get_origin, get_args, Generic
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
    org = get_origin(type_)
    if isinstance(type_, Type) and issubclass(type_, BaseSubDocument):
        assert isinstance(doc, dict)
        return {
            key: _validate_document(doc.get(field.alias if field.has_alias else key), field.outer_type_)
            for key, field in type_.__fields__.items()
        }
    elif org is not None and issubclass(org, list):
        assert isinstance(doc, list)
        t_inner = getattr(type_, '__args__', ())[0]
        return [_validate_document(value, t_inner) for value in doc]
    elif org is not None and issubclass(org, dict):
        assert isinstance(doc, dict)
        t_k_inner = getattr(type_, '__args__', ())[0]
        t_v_inner = getattr(type_, '__args__', ())[1]
        return {_validate_document(k, t_k_inner): _validate_document(v, t_v_inner) for k, v in doc.items()}
    elif issubclass(type_, date) and isinstance(doc, (int, float)):
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
