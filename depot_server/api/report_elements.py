from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, Body, HTTPException, Response
from typing import List
from uuid import UUID, uuid4

from depot_server.db import DbReportElement, collections
from depot_server.helper.auth import Authentication
from depot_server.model import ReportElement, ReportElementInWrite

router = APIRouter()


@router.get(
    '/report-elements',
    tags=['Report Element'],
    response_model=List[ReportElement],
)
async def get_report_elements(
        _user: UserInfo = Depends(Authentication()),
) -> List[ReportElement]:
    return [
        ReportElement.validate(report_element)
        async for report_element in collections.report_element_collection.find({})
    ]


@router.get(
    '/report-elements/{report_element_id}',
    tags=['Report Element'],
    response_model=ReportElement,
)
async def get_report_element(
        report_element_id: UUID,
        _user: UserInfo = Depends(Authentication()),
) -> ReportElement:
    report_element_data = await collections.report_element_collection.find_one({'_id': report_element_id})
    if report_element_data is None:
        raise HTTPException(404)
    return ReportElement.validate(report_element_data)


@router.post(
    '/report-elements',
    tags=['Report Element'],
    response_model=ReportElement,
    status_code=201,
)
async def create_report_element(
        report_element: ReportElementInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> ReportElement:
    db_report_element = DbReportElement(
        id=uuid4(),
        **report_element.dict()
    )
    await collections.report_element_collection.insert_one(db_report_element)
    return ReportElement.validate(db_report_element)


@router.put(
    '/report-elements/{report_element_id}',
    tags=['Report Element'],
    response_model=ReportElement,
)
async def update_report_element(
        report_element_id: UUID,
        report_element: ReportElementInWrite = Body(...),
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> ReportElement:
    db_report_element = DbReportElement(
        id=report_element_id,
        **report_element.dict()
    )
    if not await collections.report_element_collection.replace_one(db_report_element):
        raise HTTPException(404, f"No report_element for id {report_element_id}")
    return ReportElement.validate(db_report_element)


@router.delete(
    '/report-elements/{report_element_id}',
    tags=['Report Element'],
    status_code=204,
    response_class=Response,
)
async def delete_report_element(
        report_element_id: UUID,
        _user: UserInfo = Depends(Authentication(require_admin=True)),
) -> None:
    if not await collections.report_element_collection.delete_one({'_id': report_element_id}):
        raise HTTPException(404, f"No report_element for id {report_element_id}")
    await collections.report_profile_collection.update_many(
        {'elements': report_element_id}, {'$pull': {'elements': report_element_id}}
    )
    await collections.item_state_collection.update_many(
        {'report.report_element_id': report_element_id}, {'$pull': {'report': {'report_element_id': report_element_id}}}
    )
