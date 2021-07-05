from datetime import date, timedelta
from fastapi.testclient import TestClient

from depot_server.api import app
from depot_server.api.auth import Authentication
from depot_server.model import ReservationInWrite, Reservation, Bay, BayInWrite, ItemCondition, Item, ReservationType, \
    ReportItemInWrite, TotalReportState
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
            auth=MockAuth(sub='user1', groups=['my-team']),
        )
        assert resp.status_code == 201, resp.text
        created_reservation = Reservation.validate(resp.json())
        create_reservation.user_id = 'user1'
        assert ReservationInWrite.validate(created_reservation) == create_reservation

        resp = client.get('/api/v1/depot/reservations', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        reservations = [Reservation.validate(b) for b in resp.json()]
        assert len(reservations) == 1
        assert reservations[0] == created_reservation

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
            auth=MockAuth(sub='user2', groups=['my-team', 'my-team-upd']),
        )
        assert resp.status_code == 200, resp.text
        updated_reservation = Reservation.validate(resp.json())
        update_reservation.user_id = 'user1'
        assert ReservationInWrite.validate(updated_reservation) == update_reservation

        resp = client.delete(
            f'/api/v1/depot/reservations/{created_reservation.id}', auth=MockAuth(sub='user1')
        )
        assert resp.status_code == 200, resp.text

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
            auth=MockAuth(sub='user1', groups=['my-team']),
        )
        assert resp.status_code == 201, resp.text
        created_reservation = Reservation.validate(resp.json())
        create_reservation.user_id = 'user1'
        assert ReservationInWrite.validate(created_reservation) == create_reservation

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
