from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, Body, Query, HTTPException, BackgroundTasks, Response
from typing import List, Optional, Dict
from uuid import UUID, uuid4

from depot_server.db import collections, DbItem, DbItemState, DbStrChange, \
    DbItemStateChanges, DbItemConditionChange, DbDateChange, DbIdChange, DbTagsChange, DbTotalReportStateChange, \
    DbItemReport
from depot_server.helper.auth import Authentication
from depot_server.helper.util import utc_now
from depot_server.model import Item, ItemInWrite, ReportItemInWrite, ItemCondition, ReservationState
from ..db.model import DbReportElement
from ..mail.reservation_item_removed import send_reservation_item_removed
from ..model.item_state import ItemReport

router = APIRouter()


async def _save_state(
        prev_item: DbItem,
        new_item: DbItem,
        report: Optional[List[DbItemReport]],
        change_comment: Optional[str],
        user_id: str,
):
    changes = DbItemStateChanges()
    assert prev_item.id == new_item.id
    if prev_item.external_id != new_item.external_id:
        changes.external_id = DbStrChange(previous=prev_item.external_id, next=new_item.external_id)
    if prev_item.manufacturer != new_item.manufacturer:
        changes.manufacturer = DbStrChange(previous=prev_item.manufacturer, next=new_item.manufacturer)
    if prev_item.model != new_item.model:
        changes.model = DbStrChange(previous=prev_item.model, next=new_item.model)
    if prev_item.serial_number != new_item.serial_number:
        changes.serial_number = DbStrChange(previous=prev_item.serial_number, next=new_item.serial_number)
    if prev_item.manufacture_date != new_item.manufacture_date:
        changes.manufacture_date = DbDateChange(previous=prev_item.manufacture_date, next=new_item.manufacture_date)
    if prev_item.purchase_date != new_item.purchase_date:
        changes.purchase_date = DbDateChange(previous=prev_item.purchase_date, next=new_item.purchase_date)
    if prev_item.first_use_date != new_item.first_use_date:
        changes.first_use_date = DbDateChange(previous=prev_item.first_use_date, next=new_item.first_use_date)
    if prev_item.name != new_item.name:
        changes.name = DbStrChange(previous=prev_item.name, next=new_item.name)
    if prev_item.description != new_item.description:
        changes.description = DbStrChange(previous=prev_item.description, next=new_item.description)
    if prev_item.report_profile_id != new_item.report_profile_id:
        changes.report_profile_id = DbIdChange(previous=prev_item.report_profile_id, next=new_item.report_profile_id)
    if prev_item.total_report_state != new_item.total_report_state:
        changes.total_report_state = DbTotalReportStateChange(
            previous=prev_item.total_report_state, next=new_item.total_report_state
        )
    if prev_item.condition != new_item.condition:
        changes.condition = DbItemConditionChange(previous=prev_item.condition, next=new_item.condition)
    if prev_item.condition_comment != new_item.condition_comment:
        changes.condition_comment = DbStrChange(previous=prev_item.condition_comment, next=new_item.condition_comment)
    if prev_item.last_service != new_item.last_service:
        changes.last_service = DbDateChange(previous=prev_item.last_service, next=new_item.last_service)
    if prev_item.picture_id != new_item.picture_id:
        changes.picture_id = DbStrChange(previous=prev_item.picture_id, next=new_item.picture_id)
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
        report=report,
        user_id=user_id,
        comment=change_comment,
    ))


async def _get_report(report_profile_id: Optional[UUID], report: List[ItemReport]) -> Optional[List[DbItemReport]]:
    if report_profile_id is None:
        if report:
            raise HTTPException(404, "Report profile not set, but report is set")
        return None
    report_profile = await collections.report_profile_collection.find_one(report_profile_id)
    if report_profile is None:
        raise HTTPException(404, f"Report profile {report_profile_id} not found")
    report_elements_by_id: Dict[UUID, DbReportElement] = {
        el.id: el async for el in collections.report_element_collection.find({'_id': {'$in': report_profile.elements}})
    }
    if len(report_elements_by_id) != len(report_profile.elements):
        raise ValueError("Internal error: Report elements do not match")

    for report_entry in report:
        if report_entry.report_element_id not in report_elements_by_id:
            raise HTTPException(400, f"Invalid report element: {report_entry.report_element_id}")
    return [DbItemReport(**report_entry.dict(exclude_none=True)) for report_entry in report]


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
        item: ReportItemInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_manager=True)),
) -> Item:
    change_comment = item.change_comment
    db_item = DbItem(
        id=uuid4(),
        **item.dict(exclude_none=True, exclude={'change_comment', 'report'}),
    )
    report = await _get_report(db_item.report_profile_id, item.report)
    await collections.item_collection.insert_one(db_item)
    await _save_state(DbItem(id=db_item.id, name=""), db_item, report, change_comment, _user['sub'])
    return Item.validate(db_item)


@router.put(
    '/items/{item_id}',
    tags=['Item'],
    response_model=Item,
)
async def update_item(
        item_id: UUID,
        background_tasks: BackgroundTasks,
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
        total_report_state=item_data.total_report_state,
        last_service=item_data.last_service,
        **item.dict(exclude_none=True, exclude={'change_comment', 'last_service', 'total_report_state'})
    )
    await _save_state(item_data, db_item, None, change_comment, _user['sub'])
    if not await collections.item_collection.replace_one(db_item):
        raise HTTPException(404, f"Item {item_id} not found")
    # !Gone -> Gone -> Notify reservations
    if item_data.condition != ItemCondition.Gone and db_item.condition == ItemCondition.Gone:
        async for item_reservation in collections.item_reservation_collection.find({
            'item_id': item_id, 'end': {'$gte': utc_now()}, 'state': ReservationState.RESERVED
        }):
            reservation = await collections.reservation_collection.find_one({'_id': item_reservation.reservation_id})
            background_tasks.add_task(send_reservation_item_removed, _user, db_item, reservation)
    return Item.validate(db_item)


@router.put(
    '/items/{item_id}/report',
    tags=['Item'],
    response_model=Item,
)
async def report_item(
        item_id: UUID,
        item: ReportItemInWrite = Body(...),
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
        **item.dict(exclude_none=True, exclude={'change_comment', 'report'})
    )

    report = await _get_report(db_item.report_profile_id, item.report)

    await _save_state(item_data, db_item, report, change_comment, _user['sub'])
    if not await collections.item_collection.replace_one(db_item):
        raise HTTPException(404, f"Item {item_id} not found")
    return Item.validate(db_item)


@router.delete(
    '/items/{item_id}',
    tags=['Item'],
    status_code=204,
    response_class=Response,
)
async def delete_item(
        item_id: UUID,
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> None:
    if not await collections.item_collection.delete_one({'_id': item_id}):
        raise HTTPException(404, f"Item {item_id} not found")
