from authlib.oidc.core import UserInfo
from datetime import date
from fastapi import APIRouter, Depends, Body, Query, HTTPException
from pymongo import DESCENDING, ASCENDING
from typing import List, Optional, Set
from uuid import UUID, uuid4

from depot_server.db import collections, DbReservation
from depot_server.model import Reservation, ReservationInWrite
from .auth import Authentication

router = APIRouter()


async def _check_items(item_ids: List[UUID], start: date, end: date, skip_reservation_id: UUID = None):
    if skip_reservation_id is None:
        skip_id = {}
    else:
        skip_id = {
            '_id': {'$ne': skip_reservation_id}
        }
    safe_item_ids = [
        item['_id']
        async for item in collections.item_collection.collection.find({'_id': {'$in': item_ids}}, projection={'_id': 1})
    ]
    if len(safe_item_ids) != len(item_ids):
        raise HTTPException(404, "Some items were not found")
    item_ids_set = set(item_ids)
    async for reservation in collections.reservation_collection.collection.find({
        'items': {'$in': item_ids},
        'end': {'$gte': start.toordinal()},
        'start': {'$lte': end.toordinal()},
        **skip_id
    }, projection={'items': 1, '_id': 0}):
        if not item_ids_set.isdisjoint(reservation['items']):
            raise HTTPException(400, "Some items are already reserved")


@router.get(
    '/reservations',
    tags=['Reservation'],
    response_model=List[Reservation],
)
async def get_reservations(
        for_user: Optional[str] = Query(None),
        all_users: bool = Query(True),
        start: Optional[date] = Query(None),
        end: Optional[date] = Query(None),
        item_id: Optional[UUID] = Query(None),
        offset: Optional[int] = Query(None, ge=0),
        limit: Optional[int] = Query(None, gt=0),
        limit_before_start: Optional[int] = Query(None, gt=0),
        limit_after_end: Optional[int] = Query(None, gt=0),
        _user: UserInfo = Depends(Authentication()),
) -> List[Reservation]:
    query: dict = {}
    if for_user is not None:
        query['user_id'] = for_user
    elif not all_users:
        query['user_id'] = _user['sub']
    if item_id is not None:
        query['items'] = item_id
    if limit_before_start is not None:
        if start is None:
            raise HTTPException(400, "Require start for limit_before_start")
        before_query = {
            **query,
            'end': {'$lt': start.toordinal()},
        }
        before_start = [
            Reservation.validate(reservation)
            async for reservation in collections.reservation_collection.find(
                before_query, limit=limit_before_start, sort=[('start', DESCENDING)]
            )
        ]
    else:
        before_start = []
    if limit_after_end is not None:
        if end is None:
            raise HTTPException(400, "Require end for limit_after_end")
        after_query = {
            **query,
            'start': {'$gt': end.toordinal()}
        }
        after_end = [
            Reservation.validate(reservation)
            async for reservation in collections.reservation_collection.find(
                after_query, limit=limit_after_end, sort=[('start', ASCENDING)]
            )
        ]
        after_end.reverse()
    else:
        after_end = []

    if start is not None:
        query['end'] = {'$gte': start.toordinal()}
    if end is not None:
        query['start'] = {'$lte': end.toordinal()}

    if (limit is None or limit > 0) and (start is None or end is None or start < end):
        mid = [
            Reservation.validate(reservation)
            async for reservation in collections.reservation_collection.find(
                query, skip=offset, limit=limit, sort=[('start', DESCENDING)]
            )
        ]
    else:
        mid = []

    return before_start + mid + after_end


@router.get(
    '/reservations/items',
    tags=['Item'],
    response_model=List[UUID],
)
async def get_reservations_items(
        start: date = Query(...),
        end: date = Query(...),
        skip_reservation_id: Optional[UUID] = Query(None),
        _user: UserInfo = Depends(Authentication()),
) -> List[UUID]:
    if skip_reservation_id is None:
        skip_id: dict = {}
    else:
        skip_id = {
            '_id': {'$ne': skip_reservation_id}
        }
    item_ids: Set[UUID] = set()
    async for reservation in collections.reservation_collection.collection.find({
        'end': {'$gte': start.toordinal()},
        'start': {'$lte': end.toordinal()},
        **skip_id
    }, projection={'items': 1, '_id': 0}):
        item_ids.update(reservation['items'])

    return list(item_ids)


@router.get(
    '/reservations/{reservation_id}',
    tags=['Reservation'],
    response_model=Reservation,
)
async def get_reservation(
        reservation_id: UUID,
        _user: UserInfo = Depends(Authentication()),
) -> Reservation:
    reservation_data = await collections.reservation_collection.find_one({'_id': reservation_id})
    if reservation_data is None:
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    return Reservation.validate(reservation_data)


@router.post(
    '/reservations',
    tags=['Reservation'],
    response_model=Reservation,
    status_code=201,
)
async def create_reservation(
        reservation: ReservationInWrite = Body(...),
        _user: UserInfo = Depends(Authentication()),
) -> Reservation:
    if reservation.team_id is not None and reservation.team_id not in _user['groups']:
        raise HTTPException(400, f"User is not in team {reservation.team_id}")
    if reservation.user_id is None:
        reservation.user_id = _user['sub']
    elif reservation.user_id != _user['sub'] and 'admin' not in _user['roles']:
        raise HTTPException(400, f"Cannot set user {reservation.user_id}")
    db_reservation = DbReservation(
        id=uuid4(),
        **reservation.dict(),
    )
    await _check_items(reservation.items, reservation.start, reservation.end)
    await collections.reservation_collection.insert_one(db_reservation)
    return Reservation.validate(db_reservation)


@router.put(
    '/reservations/{reservation_id}',
    tags=['Reservation'],
    response_model=Reservation,
)
async def update_reservation(
        reservation_id: UUID,
        reservation: ReservationInWrite = Body(...),
        _user: UserInfo = Depends(Authentication()),
) -> Reservation:
    prev_reservation = await collections.reservation_collection.find_one({'_id': reservation_id})
    if prev_reservation is None:
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    if prev_reservation.user_id != _user['sub'] and (
            prev_reservation.team_id not in _user['groups'] or prev_reservation.team_id is None
    ) and 'admin' not in _user['roles']:
        raise HTTPException(403, f"Cannot modify {reservation_id}")
    if reservation.team_id is not None and reservation.team_id not in _user['groups']:
        raise HTTPException(400, f"User is not in team {reservation.team_id}")
    if reservation.user_id is None:
        reservation.user_id = _user['sub']
    elif reservation.user_id != _user['sub'] and reservation.user_id != prev_reservation.user_id and \
            'admin' not in _user['roles']:
        raise HTTPException(400, f"Cannot set user {reservation.user_id}")
    if reservation.start <= date.today() and reservation.start != prev_reservation.start \
            and 'admin' not in _user['roles']:
        raise HTTPException(400, "Cannot change start of started reservation")
    if reservation.end <= date.today() and reservation.end != prev_reservation.end \
            and 'admin' not in _user['roles']:
        raise HTTPException(400, "Cannot change end of past reservation")
    if reservation.end <= date.today() and reservation.items != prev_reservation.items \
            and 'admin' not in _user['roles']:
        raise HTTPException(400, "Cannot change items of past reservation")
    db_reservation = DbReservation(
        id=reservation_id,
        **reservation.dict()
    )
    await _check_items(reservation.items, reservation.start, reservation.end, reservation_id)
    if not await collections.reservation_collection.replace_one(db_reservation):
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    return Reservation.validate(db_reservation)


@router.delete(
    '/reservations/{reservation_id}',
    tags=['Reservation'],
)
async def delete_reservation(
        reservation_id: UUID,
        _user: UserInfo = Depends(Authentication()),
) -> None:
    reservation = await collections.reservation_collection.find_one({'_id': reservation_id})
    if reservation is None:
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    if (reservation.start <= date.today() or (reservation.user_id != _user['sub'] and (
            reservation.team_id not in _user['groups'] or reservation.team_id is None
    ))) and 'admin' not in _user['roles']:
        raise HTTPException(403, f"Cannot delete {reservation_id}")
    if not await collections.reservation_collection.delete_one({'_id': reservation_id}):
        raise HTTPException(404, f"Reservation {reservation_id} not found")
