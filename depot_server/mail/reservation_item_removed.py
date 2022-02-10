import traceback

from depot_server.db import DbItem, DbReservation
from depot_server.helper.auth import get_profile
from depot_server.mail.mailer import mailer


async def send_reservation_item_removed(sender: dict, item: DbItem, reservation: DbReservation):
    target_user = await get_profile(reservation.user_id)
    if not target_user.get('email'):
        return

    try:
        await mailer.async_send_mail(
            target_user.get('locale', 'en_us'),
            'manager_item_problem',
            target_user['email'],
            {'sender': sender, 'user': target_user, 'item': item, 'reservation': reservation},
        )
    except BaseException:
        traceback.print_exc()
