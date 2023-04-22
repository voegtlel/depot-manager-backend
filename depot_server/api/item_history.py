from authlib.oidc.core import UserInfo
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from pymongo import DESCENDING, ASCENDING
from typing import List, Optional
from uuid import UUID

from depot_server.db import collections
from depot_server.helper.auth import Authentication
from depot_server.model import ItemState

router = APIRouter()


@router.get(
    '/items/{item_id}/history',
    tags=['Item'],
    response_model=List[ItemState],
)
async def get_item_history(
        item_id: UUID,
        start: Optional[datetime] = Query(None),
        end: Optional[datetime] = Query(None),
        limit_before_start: Optional[int] = Query(None, gt=0),
        limit_after_end: Optional[int] = Query(None, gt=0),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        _user: UserInfo = Depends(Authentication()),
) -> List[ItemState]:
    if not await collections.item_collection.exists({'_id': item_id}):
        raise HTTPException(404, f"Item {item_id} not found")
    query: dict = {'item_id': item_id}

    if limit_before_start is not None:
        if start is None:
            raise HTTPException(400, "Require start for limit_before_start")
        before_query = {
            **query,
            'timestamp': {'$lt': start},
        }
        before_start = [
            ItemState.validate(item_state)
            async for item_state in collections.item_state_collection.find(
                before_query, limit=limit_before_start, sort=[('timestamp', DESCENDING)]
            )
        ]
        before_start.reverse()
    else:
        before_start = []
    if limit_after_end is not None:
        if end is None:
            raise HTTPException(400, "Require end for limit_after_end")
        after_query = {
            **query,
            'timestamp': {'$gt': end}
        }
        after_end = [
            ItemState.validate(item_state)
            async for item_state in collections.item_state_collection.find(
                after_query, limit=limit_after_end, sort=[('timestamp', ASCENDING)]
            )
        ]
    else:
        after_end = []

    if start is not None:
        query['timestamp'] = {'$gte': start}
    if end is not None:
        if 'timestamp' in query:
            query['timestamp']['$lt'] = end
        else:
            query['timestamp'] = {'$lt': end}

    return before_start + [
        ItemState.validate(item_state)
        async for item_state in collections.item_state_collection.find(
            query,
            skip=offset,
            limit=limit,
            sort=[('timestamp', DESCENDING)],
        )
    ] + after_end


@router.get(
    '/items/histories',
    tags=['Item'],
    response_model=List[ItemState],
)
async def get_items_histories(
        start: Optional[datetime] = Query(None),
        end: Optional[datetime] = Query(None),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        _user: UserInfo = Depends(Authentication()),
) -> List[ItemState]:
    query: dict = {}
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
            query,
            skip=offset,
            limit=limit,
            sort=[('timestamp', ASCENDING)],
        )
    ]
