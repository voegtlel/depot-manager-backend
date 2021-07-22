import asyncio
from typing import cast

from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from .collection import ModelCollection
from .connection import async_gridfs, startup as connection_startup, shutdown as connection_shutdown
from .model import DbBay, DbItem, DbItemState, DbReservation, DbReportElement, DbReportProfile

bay_collection: ModelCollection[DbBay]
item_collection: ModelCollection[DbItem]
item_state_collection: ModelCollection[DbItemState]
report_element_collection: ModelCollection[DbReportElement]
report_profile_collection: ModelCollection[DbReportProfile]
reservation_collection: ModelCollection[DbReservation]
item_picture_collection: AsyncIOMotorGridFSBucket
item_picture_thumbnail_collection: AsyncIOMotorGridFSBucket


async def startup():
    global bay_collection, item_collection, item_state_collection, report_element_collection, \
        report_profile_collection, reservation_collection, item_picture_collection, item_picture_thumbnail_collection

    await connection_startup()

    bay_collection = ModelCollection(DbBay)
    item_collection = ModelCollection(DbItem)
    item_state_collection = ModelCollection(DbItemState)
    report_element_collection = ModelCollection(DbReportElement)
    report_profile_collection = ModelCollection(DbReportProfile)
    reservation_collection = ModelCollection(DbReservation)
    item_picture_collection = async_gridfs('item_picture')
    item_picture_thumbnail_collection = async_gridfs('item_picture_thumbnail')
    await asyncio.gather(
        *[
            collection.create_indexes()
            for collection in [
                bay_collection, item_collection, item_state_collection, report_element_collection,
                report_profile_collection, reservation_collection
            ]
        ]
    )


async def shutdown():
    await connection_shutdown()

    global bay_collection, item_collection, item_state_collection, report_element_collection, \
        report_profile_collection, reservation_collection, item_picture_collection, item_picture_thumbnail_collection
    bay_collection = cast(ModelCollection, None)
    item_collection = cast(ModelCollection, None)
    item_state_collection = cast(ModelCollection, None)
    report_element_collection = cast(ModelCollection, None)
    report_profile_collection = cast(ModelCollection, None)
    reservation_collection = cast(ModelCollection, None)
    item_picture_collection = cast(AsyncIOMotorGridFSBucket, None)
    item_picture_thumbnail_collection = cast(AsyncIOMotorGridFSBucket, None)
