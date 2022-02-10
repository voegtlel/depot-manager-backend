import traceback
from asyncio import Task

import asyncio
from datetime import datetime, date, time, timedelta
from typing import Callable, Awaitable, Optional, Dict

from depot_server.config import config
from depot_server.db import collections
from depot_server.helper.auth import get_profile
from depot_server.mail.mailer import mailer
from depot_server.model import ReservationState


async def dayly_cron(time_of_day: time, task: Callable[[], Awaitable]):
    last_task: Optional[Task] = None
    while True:
        now = datetime.now()
        next = datetime.combine(date.today(), time_of_day)
        if next < now:
            next = datetime.combine(date.today() + timedelta(days=1), time_of_day)
        delta = (next - now).total_seconds()
        await asyncio.sleep(delta)
        if last_task is None or last_task.done():
            last_task = asyncio.create_task(task())
        else:
            print("Skipping to run next task, last did not finish")


async def task_send_reminder_mail():
    print("TASK: Send reminder mails")
    user_cache: Dict[str, dict] = {}
    send_mails = []
    if config.reservation_automatic_return:
        async for reservation in collections.reservation_collection.find({
            'state': ReservationState.RESERVED.value,
            'end': {
                '$lte': (date.today() + timedelta(days=1)).toordinal(),
            },
        }):
            reservation.state = ReservationState.RETURNED
            await collections.reservation_collection.update_one(
                {'_id': reservation.id}, {'state': ReservationState.RETURNED.value}
            )
            await collections.item_reservation_collection.update_many(
                {'reservation_id': reservation.id},
                {'$set': {'state': ReservationState.RETURNED.value}},
            )
        return
    async for reservation in collections.reservation_collection.find({
        'state': ReservationState.RESERVED,
        '$or': [
            {
                # end == today - 1d  # should have returned yesterday
                # end == today - 1w  # should have returned 1 week ago
                'end': {
                    '$in': [
                        (date.today() - timedelta(days=1)).toordinal(),
                        (date.today() - timedelta(days=7)).toordinal(),
                    ],
                },
            },
            {
                # Every day after 2w
                'end': {
                    '$lt': (date.today() + timedelta(days=14)).toordinal(),
                },
            }
        ],
    }):
        user = user_cache.get(reservation.user_id)
        if user is None:
            try:
                user = await get_profile(reservation.user_id)
            except BaseException:
                traceback.print_exc()
        if user is None:
            continue
        email = user.get('email')
        if email is None:
            continue
        print(f"TASK: Sending reminder mail to {email}")
        send_mails.append(mailer.async_send_mail(
            user.get('locale'),
            'return_reservation_reminder',
            email,
            {'user': user, 'reservation': reservation},
        ))
    for send_mail in send_mails:
        try:
            await send_mail
        except BaseException:
            traceback.print_exc()
    print("TASK: Send reminder mails DONE")


# TODO: Well, this unfortunately does not scale property, would need to run in a separate server cron job. (otherwise
#   mails will be duplicated)
#   Note: If the backend should scale, move that away. Or rather build a separate mail task queue?
_reminder_mail_task: Optional[Task] = None


async def startup():
    global _reminder_mail_task
    if _reminder_mail_task is not None:
        _reminder_mail_task.cancel()
    _reminder_mail_task = asyncio.create_task(
        dayly_cron(config.return_reservation_reminder_cron_time, task_send_reminder_mail)
    )


async def shutdown():
    global _reminder_mail_task
    if _reminder_mail_task is not None:
        _reminder_mail_task.cancel()
    _reminder_mail_task = None
