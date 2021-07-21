import traceback
from asyncio import Task

import asyncio
from datetime import datetime, date, time, timedelta
from typing import Callable, Awaitable, Optional, Dict

from depot_server.config import config
from depot_server.db import collections
from depot_server.helper.auth import get_profile
from depot_server.mail.mailer import mailer


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
    user_cache: Dict[str, dict] = {}
    send_mails = []
    async for reservation in collections.reservation_collection.find({
        'returned': False,
        'end': {
            '$in': [
                date.today() - timedelta(days=1),
                date.today() - timedelta(days=7),
            ],
            '$lt': date.today() - timedelta(days=14),
        },
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


# TODO: Well, this unfortunately does not scale property, would need to run in a separate server cron job. (otherwise
#   mails will be duplicated)
#   Note: If the backend should scale, move that away.
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
