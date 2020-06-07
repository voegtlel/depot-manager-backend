from typing import Optional

import motor.motor_asyncio

from depot_server.config import config

async_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
async_db: Optional[motor.motor_asyncio.AsyncIOMotorCollection] = None


async def startup():
    global async_client, async_db

    assert async_client is None, "Already initialized"
    assert async_db is None, "Already initialized"

    async_client = motor.motor_asyncio.AsyncIOMotorClient(config.mongo.uri)
    async_db = async_client.get_database()


async def shutdown():
    global async_client, async_db

    assert async_client is not None, "Was not initialized"
    assert async_db is not None, "Was not initialized"

    async_client.close()
    async_client = None
    async_db = None


def async_gridfs(bucket_name: str):
    return motor.motor_asyncio.AsyncIOMotorGridFSBucket(async_db, bucket_name=bucket_name, disable_md5=True)
