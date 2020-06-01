from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from depot_server.config import config

async_db: Optional[AsyncIOMotorClient] = None


async def startup():
    global async_db

    assert async_db is None, "Already initialized"

    async_db = AsyncIOMotorClient(config.mongo.uri).get_database()


async def shutdown():
    global async_db

    assert async_db is not None, "Was not initialized"

    async_db.client.close()
    async_db = None


def async_gridfs(bucket_name: str):
    import motor.motor_asyncio
    return motor.motor_asyncio.AsyncIOMotorGridFSBucket(async_db, bucket_name=bucket_name, disable_md5=True)
