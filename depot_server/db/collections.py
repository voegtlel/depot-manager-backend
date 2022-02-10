import asyncio
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from .collection import ModelCollection
from .connection import async_gridfs, startup as connection_startup, shutdown as connection_shutdown
from .model import DbBay, DbItem, DbItemState, DbReservation, DbReportElement, DbReportProfile, DbItemReservation
from ..helper.util import set_loop_attr, get_loop_attr

bay_collection: ModelCollection[DbBay] = ModelCollection(DbBay)
item_collection: ModelCollection[DbItem] = ModelCollection(DbItem)
item_state_collection: ModelCollection[DbItemState] = ModelCollection(DbItemState)
item_reservation_collection: ModelCollection[DbItemReservation] = ModelCollection(DbItemReservation)
report_element_collection: ModelCollection[DbReportElement] = ModelCollection(DbReportElement)
report_profile_collection: ModelCollection[DbReportProfile] = ModelCollection(DbReportProfile)
reservation_collection: ModelCollection[DbReservation] = ModelCollection(DbReservation)

_TEST_NO_INDEXES: bool = False


def item_picture_collection() -> AsyncIOMotorGridFSBucket:
    return get_loop_attr('item_picture_collection')


def item_picture_thumbnail_collection() -> AsyncIOMotorGridFSBucket:
    return get_loop_attr('item_picture_thumbnail_collection')


async def startup():
    await connection_startup()

    set_loop_attr('item_picture_collection', async_gridfs('item_picture'))
    set_loop_attr('item_picture_thumbnail_collection', async_gridfs('item_picture_thumbnail'))

    if not _TEST_NO_INDEXES:
        await asyncio.gather(
            *[
                collection.sync_indexes()
                for collection in ModelCollection.__collections__
            ]
        )


async def shutdown():
    await connection_shutdown()
