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
