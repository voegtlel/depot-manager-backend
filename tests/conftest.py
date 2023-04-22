from depot_server.db import collections
from .motor_mock import motor_mock

motor_mock = motor_mock

collections._TEST_NO_INDEXES = True
