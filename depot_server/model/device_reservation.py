from typing import List

from .base import BaseModel
from .bay import Bay
from .item import Item
from .reservation import Reservation


class DeviceReservation(BaseModel):
    reservation: Reservation
    items: List[Item]
    bays: List[Bay]
