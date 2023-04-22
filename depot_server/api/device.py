from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, Body, BackgroundTasks, Response
from typing import List, Tuple

from depot_server.api.reservations import reservation_action_impl
from depot_server.db import collections, DbReservation, DbItem, DbItemReservation
from depot_server.helper.auth import DeviceAuthentication
from depot_server.model import Reservation, DeviceReservation, Item, Bay, ItemCondition, User, \
    ReservationActionInWrite

router = APIRouter()


@router.get(
    '/device/reservation',
    tags=['Device'],
    response_model=DeviceReservation,
)
async def get_device_reservation(
        auth: Tuple[User, DbReservation] = Depends(DeviceAuthentication()),
) -> DeviceReservation:
    _user, reservation_data = auth
    items = []
    item_reservations = []
    async for item_reservation_doc in collections.item_reservation_collection.collection.aggregate([
        {'$match': {'reservation_id': reservation_data.id}},
        {'$lookup': {
            'from': DbItem.__collection_name__, 'localField': 'item_id', 'foreignField': '_id', 'as': 'items'
        }},
    ]):
        item_docs = item_reservation_doc.pop('items')
        item_reservations.append(DbItemReservation.validate_document(item_reservation_doc))
        for item_doc in item_docs:
            items.append(Item.validate(DbItem.validate_document(item_doc)))
    bay_ids = list({item.bay_id for item in items if item.bay_id is not None})
    if len(bay_ids):
        bays = [
            Bay.validate(bay)
            async for bay in collections.bay_collection.find({'_id': {'$in': bay_ids}})
        ]
    else:
        bays = []
    return DeviceReservation(
        reservation=Reservation.validate({**reservation_data.dict(), 'items': item_reservations}),
        items=items,
        bays=bays,
    )


@router.put(
    '/device/reservation/action',
    tags=['Device'],
    status_code=204,
    response_class=Response,
)
async def device_reservation_action(
        background_tasks: BackgroundTasks,
        action: ReservationActionInWrite = Body(...),
        auth: Tuple[User, DbReservation] = Depends(DeviceAuthentication()),
) -> None:
    user, reservation = auth

    await reservation_action_impl(
        reservation, background_tasks, action, UserInfo(user.dict())
    )


@router.get(
    '/device/items',
    tags=['Device'],
    response_model=List[Item],
)
async def get_device_items(
        _auth: Tuple[User, DbReservation] = Depends(DeviceAuthentication()),
) -> List[Item]:
    return [
        Item.validate(item)
        async for item in collections.item_collection.find({'condition': {'$ne': ItemCondition.Gone.value}})
    ]
