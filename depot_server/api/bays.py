from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, Body, HTTPException, Response
from typing import List
from uuid import UUID, uuid4

from depot_server.db import DbBay, collections
from depot_server.helper.auth import Authentication
from depot_server.model import Bay, BayInWrite

router = APIRouter()


@router.get(
    '/bays',
    tags=['Bay'],
    response_model=List[Bay],
)
async def get_bays(
        _user: UserInfo = Depends(Authentication()),
) -> List[Bay]:
    return [Bay.validate(bay) async for bay in collections.bay_collection.find({})]


@router.get(
    '/bays/{bay_id}',
    tags=['Bay'],
    response_model=Bay,
)
async def get_bay(
        bay_id: UUID,
        _user: UserInfo = Depends(Authentication()),
) -> Bay:
    bay_data = await collections.bay_collection.find_one({'_id': bay_id})
    if bay_data is None:
        raise HTTPException(404)
    return Bay.validate(bay_data)


@router.post(
    '/bays',
    tags=['Bay'],
    response_model=Bay,
    status_code=201,
)
async def create_bay(
        bay: BayInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> Bay:
    db_bay = DbBay(
        id=uuid4(),
        **bay.dict()
    )
    await collections.bay_collection.insert_one(db_bay)
    return Bay.validate(db_bay)


@router.put(
    '/bays/{bay_id}',
    tags=['Bay'],
    response_model=Bay,
)
async def update_bay(
        bay_id: UUID,
        bay: BayInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> Bay:
    db_bay = DbBay(
        id=bay_id,
        **bay.dict()
    )
    if not await collections.bay_collection.replace_one(db_bay):
        raise HTTPException(404, f"No bay for id {bay_id}")
    return Bay.validate(db_bay)


@router.delete(
    '/bays/{bay_id}',
    tags=['Bay'],
    status_code=204,
    response_class=Response,
)
async def delete_bay(
        bay_id: UUID,
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> None:
    if not await collections.bay_collection.delete_one({'_id': bay_id}):
        raise HTTPException(404, f"No bay for id {bay_id}")
    await collections.item_collection.update_many({'bay_id': bay_id}, {'$unset': {'bay_id': 1}})
