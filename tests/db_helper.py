import asyncio

from depot_server.db import collections


async def _clear_all():
    await collections.bay_collection.delete_many({})
    await collections.item_collection.delete_many({})
    await collections.item_state_collection.delete_many({})
    await collections.reservation_collection.delete_many({})


def clear_all():
    asyncio.get_event_loop().run_until_complete(_clear_all())
