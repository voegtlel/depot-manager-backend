import asyncio
import motor.motor_asyncio
import sys
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from typing import Optional

from depot_server.db import connection
from depot_server.db.migration import __migrations__
from depot_server.db.model.migration import DbMigration


async def lock_migration(migration_collection: motor.motor_asyncio.AsyncIOMotorCollection) -> DbMigration:
    retry = 0
    while retry < 100:
        try:
            return DbMigration.validate_document(await migration_collection.find_one_and_update(
                {
                    '_id': 0,
                    'lock': {'$ne': True},
                },
                {
                    '$set': {
                        'lock': True,
                    },
                    '$setOnInsert': {
                        '_id': 0,
                        'epoch': 0,
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            ))
        except DuplicateKeyError:
            await asyncio.sleep(0.1)
            retry += 1
    else:
        raise RuntimeError("Cannot lock migration")


async def amain(arg: Optional[str] = None):
    await connection.startup()
    migration_collection = connection.async_db()['migration']
    migration_state = await lock_migration(migration_collection)

    try:
        if arg == 'ls':
            for idx, step in enumerate(__migrations__):
                current = '' if migration_state.epoch != idx + 1 else " [current]"
                print(f"Step {idx}{current}: {step.__description__}")
            return

        migration_idx = migration_state.epoch
        print(f"Current Index: {migration_idx}")

        method = 'migrate'

        if arg is None:
            steps = __migrations__[migration_idx:]
        elif arg.startswith('-'):
            if migration_idx <= 0:
                return
            method = 'demigrate'
            relative = int(arg)
            if relative + migration_idx <= 0:
                steps = __migrations__[migration_idx::-1]
            else:
                steps = __migrations__[migration_idx:migration_idx + relative:-1]
        elif arg.startswith('+'):
            relative = int(arg)
            steps = __migrations__[migration_idx:migration_idx + relative]
        elif arg.isnumeric():
            absolute = int(arg)
            if absolute == 0:
                if migration_idx <= 0:
                    return
                method = 'demigrate'
                steps = __migrations__[migration_idx::-1]
            elif absolute < migration_idx:
                method = 'demigrate'
                steps = __migrations__[migration_idx:absolute:-1]
            else:
                steps = __migrations__[migration_idx:absolute]
        else:
            raise ValueError(f"Invalid argument: {arg}")

        for migration_step in steps:
            print(f"Running {method} {migration_idx}: {migration_step.__description__}")
            await getattr(migration_step, method)(connection.async_db())
            if method == 'migrate':
                migration_idx += 1
            else:
                migration_idx -= 1
            await migration_collection.update_one({'_id': 0}, {'$set': {'epoch': migration_idx}})
    finally:
        await migration_collection.update_one({'_id': 0}, {'$unset': {'lock': 1}})
    await connection.shutdown()


def main():
    if len(sys.argv) not in (1, 2):
        raise ValueError("Invalid arguments")
    asyncio.run(amain(sys.argv[1] if len(sys.argv) == 2 else None))


if __name__ == '__main__':
    main()
