import motor.motor_asyncio

from depot_server.config import config
from depot_server.helper.util import set_loop_attr, get_loop_attr


def async_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    async_db = get_loop_attr('async_db')
    if async_db is None:
        raise AttributeError("Db not initialized for loop")
    return async_db


def async_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    async_client = get_loop_attr('async_client')
    if async_client is None:
        raise AttributeError("Client not initialized for loop")
    return async_client


async def startup():
    assert get_loop_attr('async_client') is None, "Already initialized"
    assert get_loop_attr('async_db') is None, "Already initialized"

    async_client = motor.motor_asyncio.AsyncIOMotorClient(config.mongo.uri)
    set_loop_attr('async_client', async_client)
    set_loop_attr('async_db', async_client.get_database())


async def shutdown():
    async_client().close()
    set_loop_attr('async_client', None)
    set_loop_attr('async_db', None)


def async_gridfs(bucket_name: str):
    return motor.motor_asyncio.AsyncIOMotorGridFSBucket(async_db(), bucket_name=bucket_name, disable_md5=True)
