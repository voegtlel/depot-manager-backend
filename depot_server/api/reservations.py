import random
from authlib.oidc.core import UserInfo
from datetime import date
from fastapi import APIRouter, Depends, Body, Query, HTTPException, BackgroundTasks, Response
from pymongo import DESCENDING, ASCENDING
from typing import List, Optional, Set, Dict
from uuid import UUID, uuid4

from depot_server.config import config
from depot_server.db import collections, DbReservation, DbItem, DbItemReservation
from depot_server.helper.auth import Authentication
from depot_server.mail.manager_item_problem import send_manager_item_problem, ProblemItem
from depot_server.model import Reservation, ReservationInWrite, ReservationActionInWrite, ReservationState, \
    ReservationAction, ReservationItem

router = APIRouter()


async def _check_items(item_ids: List[UUID], start: date, end: date, skip_reservation_id: UUID = None):
    if skip_reservation_id is None:
        skip_id = {}
    else:
        skip_id = {
            'reservation_id': {'$ne': skip_reservation_id}
        }
    safe_item_ids = [
        item['_id']
        async for item in collections.item_collection.collection.find({'_id': {'$in': item_ids}}, projection={'_id': 1})
    ]
    if len(safe_item_ids) != len(item_ids):
        raise HTTPException(404, "Some items were not found")
    reserved_item_ids = [
        reservation_item['item_id']
        async for reservation_item in collections.item_reservation_collection.collection.find({
            'item_id': {'$in': item_ids},
            'end': {'$gte': start.toordinal()},
            'start': {'$lte': end.toordinal()},
            'state': {'$in': [ReservationState.RESERVED.value, ReservationState.TAKEN.value]},
            **skip_id
        }, projection={'item_id': 1, '_id': 0})
    ]
    if len(reserved_item_ids) > 0:
        raise HTTPException(400, f"Some items are already reserved: {reserved_item_ids}")


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
        include_inactive: Optional[bool] = Query(False),
        offset: Optional[int] = Query(None, ge=0),
        limit: Optional[int] = Query(None, gt=0),
        limit_before_start: Optional[int] = Query(None, gt=0),
        limit_after_end: Optional[int] = Query(None, gt=0),
        include_items: Optional[bool] = Query(False),
        _user: UserInfo = Depends(Authentication()),
) -> List[Reservation]:
    query: dict = {}
    if for_user is not None:
        query['user_id'] = for_user
    elif not all_users:
        query['user_id'] = _user['sub']
    if not include_inactive:
        query['active'] = True
    if limit_before_start is not None:
        if start is None:
            raise HTTPException(400, "Require start for limit_before_start")
        before_query = {
            **query,
            'end': {'$lt': start.toordinal()},
        }
        before_start = [
            Reservation.validate(reservation.dict(exclude={'code'}))
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
            Reservation.validate(reservation.dict(exclude={'code'}))
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
            Reservation.validate(reservation.dict(exclude={'code'}))
            async for reservation in collections.reservation_collection.find(
                query, skip=offset, limit=limit, sort=[('start', DESCENDING)]
            )
        ]
    else:
        mid = []

    reservations = before_start + mid + after_end
    if include_items:
        for reservation in reservations:
            reservation.items = []
        reservations_by_id = {
            reservation.id: reservation
            for reservation in reservations
        }
        async for item_reservation_entry in collections.item_reservation_collection.find({
            'reservation_id': {'$in': [reservation.id for reservation in reservations]}
        }):
            reservations_by_id[item_reservation_entry.reservation_id].items.append(ReservationItem(
                item_id=item_reservation_entry.item_id, state=item_reservation_entry.state
            ))

    return reservations


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
            'reservation_id': {'$ne': skip_reservation_id}
        }
    item_ids: Set[UUID] = {
        item_reservation['item_id']
        async for item_reservation in collections.item_reservation_collection.collection.find(
            {
                'end': {'$gte': start.toordinal()},
                'start': {'$lte': end.toordinal()},
                **skip_id
            },
            projection={'item_id': 1, '_id': 0}
        )
    }
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
    reservation = await collections.reservation_collection.find_one({'_id': reservation_id})
    if reservation is None:
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    items = [
        item_reservation
        async for item_reservation in
        collections.item_reservation_collection.find({'reservation_id': reservation_id})
    ]
    if reservation.user_id != _user['sub'] and (
            reservation.team_id not in _user.get(config.oauth2.teams_property, []) or
            reservation.team_id is None
    ) and 'admin' not in _user['roles']:
        return Reservation.validate({**reservation.dict(exclude={'code'}), 'items': items})
    return Reservation.validate({**reservation.dict(), 'items': items})


@router.post(
    '/reservations',
    tags=['Reservation'],
    response_model=Reservation,
    status_code=201,
)
async def create_reservation(
        reservation: ReservationInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_userinfo=True)),
) -> Reservation:
    if reservation.team_id is not None and reservation.team_id not in _user.get(config.oauth2.teams_property, []):
        raise HTTPException(400, f"User is not in team {reservation.team_id}")
    if reservation.user_id is None:
        reservation.user_id = _user['sub']
    elif reservation.user_id != _user['sub'] and 'admin' not in _user['roles']:
        raise HTTPException(400, f"Cannot set user {reservation.user_id}")
    if len(reservation.items) == 0:
        raise HTTPException(400, "Cannot create reservation without items")
    code = ''.join(
        random.SystemRandom().choice(config.reservation_code_chars) for _ in range(config.reservation_code_length)
    )
    db_reservation = DbReservation(
        id=uuid4(),
        code=code,
        type=reservation.type,
        state=ReservationState.RESERVED,
        active=True,
        name=reservation.name,
        start=reservation.start,
        end=reservation.end,
        user_id=reservation.user_id,
        team_id=reservation.team_id,
        contact=reservation.contact,
    )
    db_item_reservations = [
        DbItemReservation(
            id=uuid4(),
            reservation_id=db_reservation.id,
            item_id=item_id,
            state=ReservationState.RESERVED,
            start=db_reservation.start,
            end=db_reservation.end,
        )
        for item_id in reservation.items
    ]
    await _check_items(reservation.items, reservation.start, reservation.end)
    await collections.reservation_collection.insert_one(db_reservation)
    await collections.item_reservation_collection.insert_many(db_item_reservations)
    return Reservation.validate({**db_reservation.dict(), 'items': db_item_reservations})


@router.put(
    '/reservations/{reservation_id}',
    tags=['Reservation'],
    response_model=Reservation,
)
async def update_reservation(
        reservation_id: UUID,
        reservation: ReservationInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_userinfo=True)),
) -> Reservation:
    db_reservation = await collections.reservation_collection.find_one({'_id': reservation_id})
    if db_reservation is None:
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    if db_reservation.user_id != _user['sub'] and (
            db_reservation.team_id not in _user.get(config.oauth2.teams_property, []) or
            db_reservation.team_id is None
    ) and 'admin' not in _user['roles']:
        raise HTTPException(403, f"Cannot modify {reservation_id}")
    if reservation.team_id is not None and reservation.team_id not in _user.get(config.oauth2.teams_property, []) and \
            'admin' not in _user['roles']:
        raise HTTPException(400, f"User is not in team {reservation.team_id}")
    if reservation.user_id is None:
        reservation.user_id = _user['sub']
    elif reservation.user_id != _user['sub'] and reservation.user_id != db_reservation.user_id and \
            'admin' not in _user['roles']:
        raise HTTPException(400, f"Cannot set user {reservation.user_id}")
    if reservation.start <= date.today() and reservation.start != db_reservation.start and \
            'admin' not in _user['roles']:
        raise HTTPException(400, "Cannot change start of started reservation")
    if reservation.end <= date.today() and reservation.end != db_reservation.end and \
            'admin' not in _user['roles']:
        raise HTTPException(400, "Cannot change end of past reservation")
    set_item_ids = set(reservation.items)
    reserved_items: Dict[UUID, DbItemReservation] = {
        item_reservation.item_id: item_reservation
        async for item_reservation in collections.item_reservation_collection.find({'reservation_id': reservation_id})
    }
    new_items = [
        DbItemReservation(
            id=uuid4(),
            reservation_id=db_reservation.id,
            item_id=item_id,
            state=ReservationState.RESERVED,
            start=reservation.start,
            end=reservation.end,
        )
        for item_id in reservation.items
        if item_id not in reserved_items
    ]
    removed_reservation_items = [
        item_reservation
        for item_reservation in reserved_items.values()
        if item_reservation.item_id not in set_item_ids
    ]
    for item_reservation in removed_reservation_items:
        del reserved_items[item_reservation.item_id]
    update_reservation_item_ids = [
        item_reservation.id
        for item_reservation in reserved_items.values()
        if item_reservation.state == ReservationState.RESERVED and (
                item_reservation.end != reservation.end or item_reservation.start != reservation.start
        )
    ]
    for new_item in new_items:
        reserved_items[new_item.item_id] = new_item
    if (db_reservation.state == ReservationState.RETURNED or reservation.end <= date.today()) and \
            (len(removed_reservation_items) > 0 or len(new_items) > 0):
        raise HTTPException(400, "Cannot change items of past reservation")
    if len(reservation.items) == 0:
        raise HTTPException(400, "Cannot set reservation without items")
    if any(item.state == ReservationState.TAKEN for item in reserved_items.values()):
        db_reservation.state = ReservationState.TAKEN
    elif all(item.state == ReservationState.RETURNED for item in reserved_items.values()):
        db_reservation.state = ReservationState.RETURNED
    else:
        db_reservation.state = ReservationState.RESERVED
    db_reservation.name = reservation.name
    db_reservation.type = reservation.type
    db_reservation.start = reservation.start
    db_reservation.end = reservation.end
    db_reservation.user_id = reservation.user_id
    db_reservation.team_id = reservation.team_id
    db_reservation.contact = reservation.contact
    db_reservation.active = db_reservation.state != ReservationState.RETURNED
    await _check_items(reservation.items, reservation.start, reservation.end, reservation_id)
    if not await collections.reservation_collection.replace_one(db_reservation):
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    if len(update_reservation_item_ids) > 0:
        await collections.item_reservation_collection.update_many(
            {'_id': {'$in': update_reservation_item_ids}},
            {'$set': {'start': reservation.start.toordinal(), 'end': reservation.end.toordinal()}},
        )
    if len(new_items) > 0:
        await collections.item_reservation_collection.insert_many(new_items)
    if len(removed_reservation_items) > 0:
        await collections.item_reservation_collection.delete_many(
            {'_id': {'$in': [ri.id for ri in removed_reservation_items]}}
        )
    return Reservation.validate({**db_reservation.dict(), 'items': list(reserved_items.values())})


@router.delete(
    '/reservations/{reservation_id}',
    tags=['Reservation'],
    status_code=204,
    response_class=Response,
)
async def delete_reservation(
        reservation_id: UUID,
        _user: UserInfo = Depends(Authentication(require_userinfo=True)),
) -> None:
    reservation = await collections.reservation_collection.find_one({'_id': reservation_id})
    if reservation is None:
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    if reservation.state != ReservationState.RESERVED and 'admin' not in _user['roles']:
        raise HTTPException(400, f"Cannot delete taken reservation {reservation_id}")
    if reservation.user_id != _user['sub'] and (
            reservation.team_id not in _user.get(config.oauth2.teams_property, []) or
            reservation.team_id is None) and 'admin' not in _user['roles']:
        raise HTTPException(403, f"Cannot delete {reservation_id}")
    if not await collections.reservation_collection.delete_one({'_id': reservation_id}):
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    await collections.item_reservation_collection.delete_many({'reservation_id': reservation_id})


async def reservation_action_impl(
        reservation: DbReservation,
        background_tasks: BackgroundTasks,
        reservation_action: ReservationActionInWrite,
        user: UserInfo,
):
    if len(reservation_action.items) == 0:
        return

    reservation_item_by_id: Dict[UUID, DbItemReservation] = {
        item_reservation.item_id: item_reservation
        async for item_reservation in collections.item_reservation_collection.find({'reservation_id': reservation.id})
    }
    item_reservation_del: List[UUID] = []
    item_reservation_returned: List[UUID] = []
    item_reservation_taken: List[UUID] = []
    item_reservation_return_problem: List[UUID] = []

    return_items = set(item.item_id for item in reservation_action.items)
    if not return_items.issubset(reservation_item_by_id):
        raise HTTPException(400, "Items must be in reservation")
    if len(reservation_action.items) != len(return_items):
        raise HTTPException(400, "Duplicate item id in items")

    for return_item in reservation_action.items:
        item_reservation = reservation_item_by_id[return_item.item_id]
        if return_item.action == ReservationAction.Return:
            if item_reservation.state == ReservationState.RETURNED:
                raise HTTPException(400, f"Cannot return returned item {return_item.item_id}")
            item_reservation.state = ReservationState.RETURNED
            item_reservation_returned.append(item_reservation.id)
        elif return_item.action == ReservationAction.Take:
            if item_reservation.state == ReservationState.RETURNED:
                raise HTTPException(400, f"Cannot take returned item {return_item.item_id}")
            if item_reservation.state == ReservationState.TAKEN:
                raise HTTPException(400, f"Cannot take item {return_item.item_id} again")
            item_reservation.state = ReservationState.TAKEN
            item_reservation_taken.append(item_reservation.id)
        elif return_item.action == ReservationAction.Remove:
            if item_reservation.state != ReservationState.RESERVED:
                raise HTTPException(
                    400,
                    f"Cannot remove item {return_item.item_id} with state "
                    f"{item_reservation.state}"
                )
            item_reservation_del.append(item_reservation.id)
            del reservation_item_by_id[return_item.item_id]
        elif return_item.action in (ReservationAction.Broken, ReservationAction.Missing):
            if reservation_item_by_id[return_item.item_id].state == ReservationState.RESERVED:
                item_reservation_del.append(item_reservation.id)
                del reservation_item_by_id[return_item.item_id]
            else:
                item_reservation.state = ReservationState.RETURN_PROBLEM
                item_reservation_return_problem.append(item_reservation.id)
        else:
            raise NotImplementedError()

    if any(item.state == ReservationState.TAKEN for item in reservation_item_by_id.values()):
        reservation.state = ReservationState.TAKEN
    elif any(item.state == ReservationState.RESERVED for item in reservation_item_by_id.values()):
        reservation.state = ReservationState.RESERVED
    elif all(item.state in
             (ReservationState.RETURNED, ReservationState.RETURN_PROBLEM) for item in reservation_item_by_id.values()):
        reservation.state = ReservationState.RETURNED
        # End reservation earlier
        if reservation.end > date.today():
            reservation.end = date.today()

    # TODO: Actually the end of an item should be set to today, always (even if too late).
    #  Still, this is problematic if another person has already reserved the item, what happens then? Should the other
    #  item then be moved forward in time?
    #  Actually, same holds for picking up
    # TODO: Mongomock seems not to support {'end': {'$min': ['$end', today_ordinal]}} :(
    if not await collections.reservation_collection.replace_one(reservation):
        raise HTTPException(404, f"Reservation {reservation.id} could not be updated")
    if len(item_reservation_returned) > 0:
        await collections.item_reservation_collection.update_many(
            {'_id': {'$in': item_reservation_returned}},
            {'$set': {'state': ReservationState.RETURNED.value}},
        )
    if len(item_reservation_taken) > 0:
        await collections.item_reservation_collection.update_many(
            {'_id': {'$in': item_reservation_taken}},
            {'$set': {'state': ReservationState.TAKEN.value}},
        )
    if len(item_reservation_return_problem) > 0:
        await collections.item_reservation_collection.update_many(
            {'_id': {'$in': item_reservation_return_problem}},
            {'$set': {'state': ReservationState.RETURN_PROBLEM.value}},
        )
    if len(item_reservation_del) > 0:
        await collections.item_reservation_collection.delete_many(
            {'_id': {'$in': item_reservation_del}},
        )

    problem_items = [
        return_item
        for return_item in reservation_action.items
        if return_item.action in (ReservationAction.Broken, ReservationAction.Missing) or return_item.comment
    ]
    if len(problem_items) > 0:
        problem_items_by_id: Dict[UUID, DbItem] = {
            item.id: item
            async for item in collections.item_collection.find(
                {'_id': {'$in': [return_item.item_id for return_item in problem_items]}}
            )
        }
        background_tasks.add_task(
            send_manager_item_problem,
            user,
            [
                ProblemItem(
                    problem=problem_item.action.value
                    if problem_item.action in (ReservationAction.Broken, ReservationAction.Missing)
                    else None,
                    comment=problem_item.comment or "",
                    item=problem_items_by_id[problem_item.item_id],
                )
                for problem_item in problem_items if problem_item.item_id in problem_items_by_id
            ],
            reservation_action.comment,
            reservation,
        )


@router.put(
    '/reservations/{reservation_id}/action',
    tags=['Reservation'],
    status_code=204,
    response_class=Response,
)
async def reservation_action(
        reservation_id: UUID,
        background_tasks: BackgroundTasks,
        action: ReservationActionInWrite = Body(...),
        user: UserInfo = Depends(Authentication(require_userinfo=True)),
) -> None:
    reservation = await collections.reservation_collection.find_one({'_id': reservation_id})
    if reservation is None:
        raise HTTPException(404, f"Reservation {reservation_id} not found")
    if reservation.user_id != user['sub'] and (
            reservation.team_id not in user.get(config.oauth2.teams_property, []) or
            reservation.team_id is None
    ) and 'admin' not in user['roles']:
        raise HTTPException(403, f"Cannot modify {reservation_id}")

    await reservation_action_impl(reservation, background_tasks, action, user)
