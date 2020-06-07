from authlib.oidc.core import UserInfo
from datetime import date
from fastapi import APIRouter, Depends, Body, Query, HTTPException
from pymongo import DESCENDING
from typing import List, Optional
from uuid import UUID, uuid4

from depot_server.db import collections, DbItem, DbItemState, DbStrChange, \
    DbItemStateChanges, DbItemConditionChange, DbDateChange, DbIdChange, DbTagsChange
from depot_server.model import Item, ItemInWrite, ItemState
from .auth import Authentication
from .util import utc_now

router = APIRouter()


async def _save_state(prev_item: DbItem, new_item: DbItem, change_comment: Optional[str], user_id: str):
    changes = DbItemStateChanges()
    assert prev_item.id == new_item.id
    if prev_item.external_id != new_item.external_id:
        changes.external_id = DbStrChange(previous=prev_item.external_id, next=new_item.external_id)
    if prev_item.name != new_item.name:
        changes.name = DbStrChange(previous=prev_item.name, next=new_item.name)
    if prev_item.description != new_item.description:
        changes.description = DbStrChange(previous=prev_item.description, next=new_item.description)
    if prev_item.condition != new_item.condition:
        changes.condition = DbItemConditionChange(previous=prev_item.condition, next=new_item.condition)
    if prev_item.condition_comment != new_item.condition_comment:
        changes.condition_comment = DbStrChange(previous=prev_item.condition_comment, next=new_item.condition_comment)
    if prev_item.purchase_date != new_item.purchase_date:
        changes.purchase_date = DbDateChange(previous=prev_item.purchase_date, next=new_item.purchase_date)
    if prev_item.last_service != new_item.last_service:
        changes.last_service = DbDateChange(previous=prev_item.last_service, next=new_item.last_service)
    if prev_item.picture_id != new_item.picture_id:
        changes.picture_id = DbIdChange(previous=prev_item.picture_id, next=new_item.picture_id)
    if prev_item.group_id != new_item.group_id:
        changes.group_id = DbStrChange(previous=prev_item.group_id, next=new_item.group_id)
    if prev_item.tags != new_item.tags:
        changes.tags = DbTagsChange(previous=prev_item.tags, next=new_item.tags)
    if prev_item.bay_id != new_item.bay_id:
        changes.bay_id = DbIdChange(previous=prev_item.bay_id, next=new_item.bay_id)
    await collections.item_state_collection.insert_one(DbItemState(
        id=uuid4(),
        item_id=new_item.id,
        timestamp=utc_now(),
        changes=changes,
        user_id=user_id,
        comment=change_comment,
    ))


@router.get(
    '/items',
    tags=['Item'],
    response_model=List[Item],
)
async def get_items(
        all: bool = Query(False),
        _user: UserInfo = Depends(Authentication()),
) -> List[Item]:
    return [
        Item.validate(item)
        async for item in collections.item_collection.find({} if all else {'condition': {'$ne': 'gone'}})
    ]


@router.get(
    '/items/{item_id}',
    tags=['Item'],
    response_model=Item,
)
async def get_item(
        item_id: UUID,
        _user: UserInfo = Depends(Authentication()),
) -> Item:
    item_data = await collections.item_collection.find_one({'_id': item_id})
    if item_data is None:
        raise HTTPException(404, f"Item {item_id} not found")
    return Item.validate(item_data)


@router.post(
    '/items',
    tags=['Item'],
    response_model=Item,
    status_code=201,
)
async def create_item(
        item: ItemInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_manager=True)),
) -> Item:
    change_comment = item.change_comment
    db_item = DbItem(
        id=uuid4(),
        **item.dict(exclude_none=True, exclude={'change_comment'}),
    )
    await collections.item_collection.insert_one(db_item)
    await _save_state(DbItem(id=db_item.id, name=""), db_item, change_comment, _user['sub'])
    return Item.validate(db_item)


@router.put(
    '/items/{item_id}',
    tags=['Item'],
    response_model=Item,
)
async def update_item(
        item_id: UUID,
        item: ItemInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_manager=True)),
) -> Item:
    item_data = await collections.item_collection.find_one({'_id': item_id})
    if item_data is None:
        raise HTTPException(404, f"Item {item_id} not found")
    change_comment = item.change_comment
    if item.bay_id is not None:
        if not await collections.bay_collection.exists({'_id': item.bay_id}):
            raise HTTPException(404, f"Bay {item.bay_id} not found")
    db_item = DbItem(
        id=item_id,
        **item.dict(exclude_none=True, exclude={'change_comment'})
    )
    await _save_state(item_data, db_item, change_comment, _user['sub'])
    if not await collections.item_collection.replace_one(db_item):
        raise HTTPException(404, f"Item {item_id} not found")
    return Item.validate(db_item)


@router.delete(
    '/items/{item_id}',
    tags=['Item'],
)
async def delete_item(
        item_id: UUID,
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> None:
    if not await collections.item_collection.delete_one({'_id': item_id}):
        raise HTTPException(404, f"Item {item_id} not found")


@router.get(
    '/items/{item_id}/history',
    tags=['Item'],
    response_model=List[ItemState],
)
async def get_item_history(
        item_id: UUID,
        start: Optional[date] = Query(None),
        end: Optional[date] = Query(None),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        _user: UserInfo = Depends(Authentication()),
) -> List[ItemState]:
    if not await collections.item_collection.exists({'_id': item_id}):
        raise HTTPException(404, f"Item {item_id} not found")
    query: dict = {'item_id': item_id}
    if start is not None:
        query['timestamp'] = {'$gte': start}
    if end is not None:
        if 'timestamp' in query:
            query['timestamp']['$lt'] = end
        else:
            query['timestamp'] = {'$lt': end}
    return [
        ItemState.validate(item_state)
        async for item_state in collections.item_state_collection.find(
            {'item_id': item_id},
            skip=offset,
            limit=limit,
            sort=[('timestamp', DESCENDING)],
        )
    ]
