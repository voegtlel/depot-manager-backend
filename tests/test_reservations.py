from datetime import date, timedelta
from fastapi.testclient import TestClient
from typing import List, Optional

import depot_server.api.reservations
from depot_server.api import app
from depot_server.db import DbReservation
from depot_server.helper.auth import Authentication
from depot_server.mail.manager_item_problem import ProblemItem
from depot_server.model import ReservationInWrite, Reservation, Bay, BayInWrite, ItemCondition, Item, ReservationType, \
    ReportItemInWrite, TotalReportState, ReservationItem, ReservationState, ReservationActionInWrite, \
    ReservationItemState, ReservationAction
from tests.db_helper import clear_all
from tests.mock_auth import MockAuthentication, MockAuth


def test_reservation(monkeypatch, motor_mock):
    monkeypatch.setattr(Authentication, '__call__', MockAuthentication.__call__)

    with TestClient(app) as client:
        clear_all()

        create_bay = BayInWrite(external_id='bay_1', name="Bay 1", description="Top Left")
        resp = client.post(
            '/api/v1/depot/bays', data=create_bay.json(), auth=MockAuth(sub='admin1', roles=['admin']),
        )
        assert resp.status_code == 201, resp.text
        created_bay_1 = Bay.validate(resp.json())

        item_ids = []
        for i in range(3):
            create_item = ReportItemInWrite(
                external_id=f'item_{i}',
                name=f"Item {i}",
                description=f"{i}. Item",
                total_report_state=TotalReportState.Fit,
                condition=ItemCondition.Good,
                condition_comment="Very Good",
                purchase_date=date.today(),
                picture_id=None,
                group_id=f'item_group_{i}',
                tags=['item'],
                bay_id=created_bay_1.id,
                change_comment="Created",
                report_profile_id=None,
                report=[],
            )
            resp = client.post(
                '/api/v1/depot/items', data=create_item.json(), auth=MockAuth(sub='admin1', roles=['admin']),
            )
            assert resp.status_code == 201, resp.text
            created_item = Item.validate(resp.json())
            item_ids.append(created_item.id)

        create_reservation = ReservationInWrite(
            type=ReservationType.PRIVATE,
            name="My Reservation",
            start=date.today() + timedelta(days=5),
            end=date.today() + timedelta(days=8),
            team_id='my-team',
            contact="12345",
            items=item_ids,
        )
        resp = client.post(
            '/api/v1/depot/reservations',
            data=create_reservation.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 201, resp.text
        created_reservation = Reservation.validate(resp.json())
        create_reservation.user_id = 'user1'
        assert created_reservation.dict(exclude={'id', 'items', 'code', 'state', 'active'}) == create_reservation.dict(exclude={'items'})
        assert len(created_reservation.code) == 6
        assert created_reservation.state == ReservationState.RESERVED
        assert created_reservation.active is True
        assert created_reservation.items == [ReservationItem(item_id=item_id, state=ReservationState.RESERVED) for item_id in item_ids]
        assert created_reservation.code is not None

        resp = client.get('/api/v1/depot/reservations', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        reservations = [Reservation.validate(b) for b in resp.json()]
        assert len(reservations) == 1
        assert reservations[0].json(exclude={'code', 'items'}) == created_reservation.json(exclude={'code', 'items'})

        resp = client.get(f'/api/v1/depot/reservations/{created_reservation.id}', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        assert Reservation.validate(resp.json()) == created_reservation

        update_reservation = ReservationInWrite(
            type=ReservationType.TEAM,
            name="My Reservation Upd",
            start=date.today() + timedelta(days=6),
            end=date.today() + timedelta(days=9),
            user_id='user1',
            team_id='my-team-upd',
            contact="123456789",
            items=[item_ids[0]],
        )
        resp = client.put(
            f'/api/v1/depot/reservations/{created_reservation.id}',
            data=update_reservation.json(),
            auth=MockAuth(sub='user2', teams=['my-team', 'my-team-upd']),
        )
        assert resp.status_code == 200, resp.text
        updated_reservation = Reservation.validate(resp.json())
        update_reservation.user_id = 'user1'
        assert updated_reservation.items == [ReservationItem(item_id=item_ids[0], state=ReservationState.RESERVED)]
        assert updated_reservation.dict(exclude={'id', 'items', 'code', 'state', 'active'}) == update_reservation.dict(exclude={'items'})

        resp = client.delete(
            f'/api/v1/depot/reservations/{created_reservation.id}', auth=MockAuth(sub='user1')
        )
        assert resp.status_code == 204, resp.text

        resp = client.get('/api/v1/depot/reservations', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 0


def test_overlap(monkeypatch, motor_mock):
    monkeypatch.setattr(Authentication, '__call__', MockAuthentication.__call__)

    with TestClient(app) as client:
        clear_all()

        create_bay = BayInWrite(external_id='bay_1', name="Bay 1", description="Top Left")
        resp = client.post(
            '/api/v1/depot/bays', data=create_bay.json(), auth=MockAuth(sub='admin1', roles=['admin']),
        )
        assert resp.status_code == 201, resp.text
        created_bay_1 = Bay.validate(resp.json())

        item_ids = []
        for i in range(3):
            create_item = ReportItemInWrite(
                external_id=f'item_{i}',
                name=f"Item {i}",
                description=f"{i}. Item",
                total_report_state=TotalReportState.Fit,
                condition=ItemCondition.Good,
                condition_comment="Very Good",
                purchase_date=date.today(),
                last_service=date.today(),
                picture_id=None,
                group_id=f'item_group_{i}',
                tags=['item'],
                bay_id=created_bay_1.id,
                change_comment="Created",
                report_profile_id=None,
                report=[],
            )
            resp = client.post(
                '/api/v1/depot/items', data=create_item.json(), auth=MockAuth(sub='admin1', roles=['admin']),
            )
            assert resp.status_code == 201, resp.text
            created_item = Item.validate(resp.json())
            item_ids.append(created_item.id)

        create_reservation = ReservationInWrite(
            type=ReservationType.PRIVATE,
            name="My Reservation",
            start=date.today() + timedelta(days=5),
            end=date.today() + timedelta(days=8),
            team_id='my-team',
            contact="12345",
            items=item_ids,
        )
        resp = client.post(
            '/api/v1/depot/reservations',
            data=create_reservation.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 201, resp.text
        created_reservation = Reservation.validate(resp.json())

        create_reservation = ReservationInWrite(
            type=ReservationType.PRIVATE,
            name="My Reservation 2",
            start=date.today() + timedelta(days=8),
            end=date.today() + timedelta(days=9),
            contact="12345",
            items=item_ids[2:],
        )
        resp = client.post(
            '/api/v1/depot/reservations',
            data=create_reservation.json(),
            auth=MockAuth(sub='user2'),
        )
        assert resp.status_code == 400, resp.text

        create_reservation = ReservationInWrite(
            type=ReservationType.PRIVATE,
            name="My Reservation 2",
            start=date.today() + timedelta(days=4),
            end=date.today() + timedelta(days=5),
            contact="12345",
            items=item_ids[:1],
        )
        resp = client.post(
            '/api/v1/depot/reservations',
            data=create_reservation.json(),
            auth=MockAuth(sub='user2'),
        )
        assert resp.status_code == 400, resp.text

        start = (date.today() + timedelta(days=4)).isoformat()
        end = (date.today() + timedelta(days=5)).isoformat()
        resp = client.get(
            f'/api/v1/depot/reservations/items?start={start}&end={end}',
            auth=MockAuth(sub='user2'),
        )
        assert resp.status_code == 200, resp.text
        assert set(resp.json()) == set(str(item_id) for item_id in item_ids)

        start = (date.today() + timedelta(days=8)).isoformat()
        end = (date.today() + timedelta(days=9)).isoformat()
        resp = client.get(
            f'/api/v1/depot/reservations/items?start={start}&end={end}',
            auth=MockAuth(sub='user2'),
        )
        assert resp.status_code == 200, resp.text
        assert set(resp.json()) == set(str(item_id) for item_id in item_ids)

        start = (date.today() + timedelta(days=4)).isoformat()
        end = (date.today() + timedelta(days=5)).isoformat()
        resp = client.get(
            f'/api/v1/depot/reservations/items?start={start}&end={end}&skip_reservation_id={created_reservation.id}',
            auth=MockAuth(sub='user2'),
        )
        assert resp.status_code == 200, resp.text
        assert set(resp.json()) == set()


def test_take_return(monkeypatch, motor_mock):
    monkeypatch.setattr(Authentication, '__call__', MockAuthentication.__call__)

    send_sender: Optional[dict] = None
    send_items: Optional[List[ProblemItem]] = None
    send_comment: Optional[str] = None
    send_reservation: Optional[DbReservation] = None

    async def mock_send_manager_item_problem(sender: dict, items: List[ProblemItem], comment: Optional[str], reservation: Optional[DbReservation]):
        nonlocal send_sender, send_items, send_comment, send_reservation
        send_sender = sender
        send_items = items
        send_comment = comment
        send_reservation = reservation

    monkeypatch.setattr(depot_server.api.reservations, 'send_manager_item_problem', mock_send_manager_item_problem)

    with TestClient(app) as client:
        clear_all()

        create_bay = BayInWrite(external_id='bay_1', name="Bay 1", description="Top Left")
        resp = client.post(
            '/api/v1/depot/bays', data=create_bay.json(), auth=MockAuth(sub='admin1', roles=['admin']),
        )
        assert resp.status_code == 201, resp.text
        created_bay_1 = Bay.validate(resp.json())

        item_ids = []
        for i in range(4):
            create_item = ReportItemInWrite(
                external_id=f'item_{i}',
                name=f"Item {i}",
                description=f"{i}. Item",
                total_report_state=TotalReportState.Fit,
                condition=ItemCondition.Good,
                condition_comment="Very Good",
                purchase_date=date.today(),
                picture_id=None,
                group_id=f'item_group_{i}',
                tags=['item'],
                bay_id=created_bay_1.id,
                change_comment="Created",
                report_profile_id=None,
                report=[],
            )
            resp = client.post(
                '/api/v1/depot/items', data=create_item.json(), auth=MockAuth(sub='admin1', roles=['admin']),
            )
            assert resp.status_code == 201, resp.text
            created_item = Item.validate(resp.json())
            item_ids.append(created_item.id)

        create_reservation = ReservationInWrite(
            type=ReservationType.PRIVATE,
            name="My Reservation",
            start=date.today() + timedelta(days=5),
            end=date.today() + timedelta(days=8),
            team_id='my-team',
            contact="12345",
            items=item_ids,
        )
        resp = client.post(
            '/api/v1/depot/reservations',
            data=create_reservation.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 201, resp.text
        created_reservation = Reservation.validate(resp.json())

        take_action = ReservationActionInWrite(items=[
            ReservationItemState(item_id=item_ids[0], action=ReservationAction.Take)
        ])
        resp = client.put(
            f'/api/v1/depot/reservations/{created_reservation.id}/action',
            data=take_action.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 204, resp.text

        resp = client.get(
            f'/api/v1/depot/reservations/{created_reservation.id}',
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 200, resp.text
        taken_reservation_1 = Reservation.validate(resp.json())
        assert taken_reservation_1.items[0].state == ReservationState.TAKEN
        assert taken_reservation_1.items[1].state == ReservationState.RESERVED
        assert taken_reservation_1.items[2].state == ReservationState.RESERVED
        assert taken_reservation_1.items[3].state == ReservationState.RESERVED
        assert taken_reservation_1.state == ReservationState.TAKEN

        resp = client.get(
            f'/api/v1/depot/items/{item_ids[0]}',
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 200, resp.text
        item_0 = Item.validate(resp.json())

        resp = client.get(
            f'/api/v1/depot/items/{item_ids[1]}',
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 200, resp.text
        item_1 = Item.validate(resp.json())

        take_action = ReservationActionInWrite(items=[ReservationItemState(item_id=item_ids[1], action=ReservationAction.Broken, comment="Hello")])
        resp = client.put(
            f'/api/v1/depot/reservations/{created_reservation.id}/action',
            data=take_action.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 204, resp.text

        # Problematic item should be gone now
        resp = client.get(
            f'/api/v1/depot/reservations/{created_reservation.id}',
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 200, resp.text
        taken_reservation_1 = Reservation.validate(resp.json())
        assert len(taken_reservation_1.items) == 3
        assert taken_reservation_1.items[0].state == ReservationState.TAKEN
        assert taken_reservation_1.items[1].state == ReservationState.RESERVED
        assert taken_reservation_1.items[2].state == ReservationState.RESERVED
        assert taken_reservation_1.state == ReservationState.TAKEN

        assert send_sender == {'roles': [], 'sub': 'user1', 'teams': ['my-team']}
        assert len(send_items) == 1
        assert send_items[0].comment == 'Hello'
        assert send_items[0].problem == "broken"
        assert send_items[0].item.id == item_ids[1]
        assert send_comment is None
        assert send_reservation.id == created_reservation.id
        send_sender = None
        send_items = None
        send_comment = None
        send_reservation = None

        take_action = ReservationActionInWrite(items=[ReservationItemState(item_id=item_ids[2], action=ReservationAction.Take, comment="World")], comment="Oh")
        resp = client.put(
            f'/api/v1/depot/reservations/{created_reservation.id}/action',
            data=take_action.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 204, resp.text

        assert send_sender == {'roles': [], 'sub': 'user1', 'teams': ['my-team']}
        assert len(send_items) == 1
        assert send_items[0].comment == 'World'
        assert send_items[0].problem is None
        assert send_items[0].item.id == item_ids[2]
        assert send_comment == 'Oh'
        assert send_reservation.id == created_reservation.id
        send_sender = None
        send_items = None
        send_comment = None
        send_reservation = None

        return_action = ReservationActionInWrite(items=[ReservationItemState(item_id=item_ids[0], action=ReservationAction.Return)])
        resp = client.put(
            f'/api/v1/depot/reservations/{created_reservation.id}/action',
            data=return_action.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 204, resp.text

        resp = client.get(
            f'/api/v1/depot/reservations/{created_reservation.id}',
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 200, resp.text
        taken_reservation_1 = Reservation.validate(resp.json())
        assert len(taken_reservation_1.items) == 3
        assert taken_reservation_1.items[0].state == ReservationState.RETURNED
        assert taken_reservation_1.items[1].state == ReservationState.TAKEN
        assert taken_reservation_1.items[2].state == ReservationState.RESERVED
        assert taken_reservation_1.state == ReservationState.TAKEN

        take_action = ReservationActionInWrite(items=[ReservationItemState(item_id=item_ids[3], action=ReservationAction.Take)])
        resp = client.put(
            f'/api/v1/depot/reservations/{created_reservation.id}/action',
            data=take_action.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 204, resp.text

        return_action = ReservationActionInWrite(items=[
            ReservationItemState(item_id=item_ids[2], action=ReservationAction.Return),
            ReservationItemState(item_id=item_ids[3], action=ReservationAction.Broken, comment="Something"),
        ])
        resp = client.put(
            f'/api/v1/depot/reservations/{created_reservation.id}/action',
            data=return_action.json(),
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 204, resp.text

        resp = client.get(
            f'/api/v1/depot/reservations/{created_reservation.id}',
            auth=MockAuth(sub='user1', teams=['my-team']),
        )
        assert resp.status_code == 200, resp.text
        taken_reservation_1 = Reservation.validate(resp.json())
        assert len(taken_reservation_1.items) == 3
        assert taken_reservation_1.items[0].state == ReservationState.RETURNED
        assert taken_reservation_1.items[1].state == ReservationState.RETURNED
        assert taken_reservation_1.items[2].state == ReservationState.RETURN_PROBLEM
        assert taken_reservation_1.state == ReservationState.RETURNED

        assert send_sender == {'roles': [], 'sub': 'user1', 'teams': ['my-team']}
        assert len(send_items) == 1
        assert send_items[0].comment == 'Something'
        assert send_items[0].problem == "broken"
        assert send_items[0].item.id == item_ids[3]
        assert send_comment is None
        assert send_reservation.id == created_reservation.id
