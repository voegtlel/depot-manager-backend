from typing import TypeVar, Generic, Type, Any, List, Tuple, AsyncIterable, Optional, Iterable

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import OperationFailure

from depot_server.db.model.base import BaseDocument

TModel = TypeVar('TModel', bound=BaseDocument)


class ModelCollection(Generic[TModel]):
    def __init__(self, collection_model: Type[TModel]):
        from depot_server.db import connection

        self.collection_model = collection_model
        assert connection.async_db is not None, "Database not initialized"
        self.collection: AsyncIOMotorCollection = connection.async_db[collection_model.__collection_name__]

    async def create_indexes(self):
        idx = getattr(self.collection_model, '__indexes__', None)
        if idx:
            try:
                created_indexes = await self.collection.create_indexes(idx)
                if created_indexes:
                    print(f"Created indexes {created_indexes} for {self.collection.name}")
            except OperationFailure:
                await self.collection.drop_indexes()
                created_indexes = await self.collection.create_indexes(idx)
                if created_indexes:
                    print(f"Recreated indexes {created_indexes} for {self.collection.name}")

    async def insert_one(
            self, document: TModel, **kwargs
    ) -> None:
        await self.collection.insert_one(document.document(), **kwargs)

    async def insert_many(
            self, documents: Iterable[TModel], **kwargs
    ) -> None:
        await self.collection.insert_one((document.document() for document in documents), **kwargs)

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
