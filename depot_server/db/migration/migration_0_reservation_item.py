from uuid import uuid4

import motor.motor_asyncio
import random
from datetime import date

from depot_server.config import config

__description__ = "Store state of reservation items"


def gencode():
    return ''.join(
        random.SystemRandom().choice(config.reservation_code_chars)
        for _ in range(config.reservation_code_length)
    )


async def migrate(db: motor.motor_asyncio.AsyncIOMotorDatabase):
    now = date.today().toordinal()
    async for reservation in db['reservation'].find({}):
        if 'active' in reservation:
            print(f"  Skip reservation {reservation['_id']}")
            continue
        update = [{'$set': {}}, {'$unset': 'items'}]
        if reservation['start'] < now:
            reservation_state = 'reserved'
            update[0]['$set']['active'] = True
            update[0]['$set']['code'] = gencode()
        elif reservation['end'] > now:
            reservation_state = 'returned'
            update[0]['$set']['active'] = True
            update[0]['$set']['code'] = gencode()
        else:
            reservation_state = 'taken'
            update.append({'$unset': {'active': 1}})
        update[0]['$set']['state'] = reservation_state
        if len(reservation['items']) > 0:
            await db['itemReservation'].insert_many(
                [
                    {
                        '_id': uuid4(),
                        'reservation_id': reservation['_id'],
                        'item_id': item_id,
                        'state': reservation_state,
                        'start': reservation['start'],
                        'end': reservation['end'],
                    }
                    for item_id in reservation['items']
                ]
            )
        await db['reservation'].update_one(
            {'_id': reservation['_id']},
            update
        )
        print(f"  Migrated reservation {reservation['_id']}")


async def demigrate(db: motor.motor_asyncio.AsyncIOMotorDatabase):
    async for reservation in db['reservation'].find({}):
        if 'active' not in reservation:
            print(f"  Skip reservation {reservation['_id']}")
            continue
        items = [
            reserved_item['item_id']
            async for reserved_item in db['itemReservation'].find({'reservation_id': reservation['_id']})
        ]
        await db['reservation'].update_one(
            {'_id': reservation['_id']},
            [
                {
                    '$set': {
                        'items': items
                    },
                },
                {
                    '$unset': [
                        'state',
                        'active',
                        'code',
                    ],
                },
            ],
        )
        await db['itemReservation'].delete_many({'reservation_id': reservation['_id']})
        print(f"  Migrated reservation {reservation['_id']}")
