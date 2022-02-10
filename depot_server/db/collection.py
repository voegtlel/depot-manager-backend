from pymongo.errors import OperationFailure
from typing import TypeVar, Generic, Type, Any, List, Tuple, AsyncIterable, Optional, Iterable, ClassVar

from depot_server.db.model.base import BaseDocument

from motor.core import AgnosticCollection


TModel = TypeVar('TModel', bound=BaseDocument)


class ModelCollection(Generic[TModel]):
    __collections__: ClassVar[List['ModelCollection']] = []
    collection_model: Type[TModel]

    def __init__(self, collection_model: Type[TModel]):
        self.collection_model = collection_model
        self.__collections__.append(self)

    @property
    def collection(self) -> AgnosticCollection:
        from depot_server.db import connection
        return connection.async_db()[self.collection_model.__collection_name__]

    async def sync_indexes(self):
        indexes = self.collection_model.__indexes__
        # Drop gone indexes
        keys = [
            idx.document['key']
            for idx in indexes
        ]
        async for existing_idx in self.collection.list_indexes():
            if existing_idx['key'] not in keys and existing_idx['name'] != '_id_':
                await self.collection.drop_index(existing_idx['name'])
                print(f"Dropped index {existing_idx} for {self.collection.name}")
        # (Re)create new indexes
        if len(indexes) > 0:
            try:
                created_indexes = await self.collection.create_indexes(indexes)
                if created_indexes:
                    print(f"Created indexes {created_indexes} for {self.collection.name}")
            except OperationFailure:
                await self.collection.drop_indexes()
                created_indexes = await self.collection.create_indexes(indexes)
                if created_indexes:
                    print(f"Recreated indexes {created_indexes} for {self.collection.name}")

    async def insert_one(
            self, document: TModel, **kwargs
    ) -> None:
        await self.collection.insert_one(document.document(), **kwargs)

    async def insert_many(
            self, documents: Iterable[TModel], **kwargs
    ) -> None:
        await self.collection.insert_many([document.document() for document in documents], **kwargs)

    async def find(
            self, filter: Any, skip: int = None, limit: int = None, sort: List[Tuple[str, int]] = None, **kwargs
    ) -> AsyncIterable[TModel]:
        if skip is not None and skip != 0:
            kwargs['skip'] = skip
        if limit is not None and limit != 0:
            kwargs['limit'] = limit
        async for data in self.collection.find(filter, sort=sort, **kwargs):
            yield self.collection_model.validate_document(data)

    async def find_one(
            self, filter: Any, **kwargs
    ) -> Optional[TModel]:
        data = await self.collection.find_one(filter, **kwargs)
        if data is None:
            return None
        return self.collection_model.validate_document(data)

    async def replace_one(
            self, replacement: TModel, **kwargs
    ) -> bool:
        doc = replacement.document()
        id = doc['_id']
        del doc['_id']
        res = await self.collection.replace_one({'_id': id}, doc, **kwargs)
        return res.matched_count == 1

    async def update_one(
            self, filter: Any, update: Any, **kwargs
    ) -> bool:
        res = await self.collection.update_one(filter, update, **kwargs)
        return res.matched_count == 1

    async def update_many(
            self, filter: Any, update: Any, **kwargs
    ) -> None:
        await self.collection.update_many(filter, update, **kwargs)

    async def delete_one(
            self, filter: Any, **kwargs
    ) -> bool:
        res = await self.collection.delete_one(filter, **kwargs)
        return res.deleted_count == 1

    async def delete_many(
            self, filter: Any, **kwargs
    ) -> None:
        await self.collection.delete_many(filter, **kwargs)

    async def count_documents(
            self, filter: Any, **kwargs
    ) -> int:
        return await self.collection.count_documents(filter, **kwargs)

    async def exists(
            self, filter: Any
    ) -> bool:
        return await self.count_documents(filter, limit=1) != 0
