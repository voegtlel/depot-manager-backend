from datetime import date, timedelta

from fastapi.testclient import TestClient

from depot_server.api import app
from depot_server.helper.auth import Authentication
from depot_server.model import ItemInWrite, Item, ItemCondition, ItemState, BayInWrite, Bay, TotalReportState, \
    ReportItemInWrite, ReportState
from depot_server.model.item_state import ItemReport
from tests.db_helper import clear_all
from tests.mock_auth import MockAuthentication, MockAuth
from tests.test_report import _create_report_profile


def test_item(monkeypatch, motor_mock):
    monkeypatch.setattr(Authentication, '__call__', MockAuthentication.__call__)

    with TestClient(app) as client:
        clear_all()

        create_bay = BayInWrite(external_id='bay_1', name="Bay 1", description="Top Left")
        resp = client.post(
            '/api/v1/depot/bays', data=create_bay.json(), auth=MockAuth(sub='admin1', roles=['admin']),
        )
        assert resp.status_code == 201, resp.text
        created_bay_1 = Bay.validate(resp.json())

        report_profile, (report_element_1, report_element_2) = _create_report_profile(client)

        create_item = ReportItemInWrite(
            external_id='item_1',
            name="Item 1",
            description="First Item",
            total_report_state=TotalReportState.Fit,
            condition=ItemCondition.Good,
            condition_comment="Very Good",
            purchase_date=date.today(),
            last_service=date.today(),
            picture_id=None,
            group_id='item_group_1',
            tags=['item', 'one'],
            bay_id=created_bay_1.id,
            change_comment="Created",
            report_profile_id=report_profile.id,
            report=[
                ItemReport(report_element_id=report_element_1.id, state=ReportState.Good),
                ItemReport(report_element_id=report_element_2.id, state=ReportState.Monitor, comment="Okish"),
            ],
        )
        resp = client.post(
            '/api/v1/depot/items', data=create_item.json(), auth=MockAuth(sub='admin1', roles=['admin']),
        )
        assert resp.status_code == 201, resp.text
        created_item = Item.validate(resp.json())
        assert created_item.dict(exclude={'id', 'reservation_id'}) == create_item.dict(exclude={'change_comment', 'report'})

        resp = client.get('/api/v1/depot/items', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        items = [Item.validate(b) for b in resp.json()]
        assert len(items) == 1
        assert items[0] == created_item

        resp = client.get(f'/api/v1/depot/items/{created_item.id}', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        assert Item.validate(resp.json()) == created_item

        update_item = ItemInWrite(
            external_id='item_1_upd',
            name="Item 1 Upd",
            description="First Item Updated",
            condition=ItemCondition.Bad,
            condition_comment="Very Bad",
            purchase_date=date.today() + timedelta(days=2),
            picture_id=None,
            group_id=None,
            tags=['item', 'two'],
            bay_id=None,
            change_comment="Updated",
        )
        resp = client.put(
            f'/api/v1/depot/items/{created_item.id}',
            data=update_item.json(),
            auth=MockAuth(sub='admin2', roles=['admin'])
        )
        assert resp.status_code == 200, resp.text
        updated_item = Item.validate(resp.json())
        assert updated_item.dict(exclude={'id', 'reservation_id', 'total_report_state', 'last_service'}) == update_item.dict(exclude={'change_comment'})

        report_item = ReportItemInWrite(
            external_id='item_1_rprt',
            name="Item 1 Reprt",
            description="First Item Reported",
            condition=ItemCondition.Ok,
            condition_comment="Okish",
            purchase_date=date.today() + timedelta(days=2),
            last_service=date.today() + timedelta(days=3),
            picture_id=None,
            group_id=None,
            tags=['item', 'two', 'three'],
            bay_id=None,
            change_comment="Reported",
            report_profile_id=report_profile.id,
            total_report_state=TotalReportState.Fit,
            report=[
                ItemReport(report_element_id=report_element_1.id, state=ReportState.Monitor, comment="Okish 2"),
                ItemReport(report_element_id=report_element_2.id, state=ReportState.Good),
            ],
        )
        resp = client.put(
            f'/api/v1/depot/items/{created_item.id}/report',
            data=report_item.json(),
            auth=MockAuth(sub='admin2', roles=['admin'])
        )
        assert resp.status_code == 200, resp.text
        reported_item = Item.validate(resp.json())
        assert reported_item.dict(exclude={'id', 'reservation_id'}) == report_item.dict(exclude={'change_comment', 'report'})

        resp = client.get(f'/api/v1/depot/items/{created_item.id}/history', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        states = [ItemState.validate(r) for r in resp.json()]
        assert len(states) == 3
        assert states[0].user_id == 'admin2'
        assert states[0].item_id == created_item.id
        assert states[0].comment == 'Reported'
        assert states[0].changes.external_id.next == reported_item.external_id
        assert states[0].changes.name.next == reported_item.name
        assert states[0].changes.description.next == reported_item.description
        assert states[0].changes.condition.next == reported_item.condition
        assert states[0].changes.condition_comment.next == reported_item.condition_comment
        assert states[0].changes.last_service.next == reported_item.last_service
        assert states[0].changes.tags.next == reported_item.tags
        assert states[1].user_id == 'admin2'
        assert states[1].item_id == created_item.id
        assert states[1].comment == 'Updated'
        assert states[1].changes.external_id.next == update_item.external_id
        assert states[1].changes.name.next == update_item.name
        assert states[1].changes.description.next == update_item.description
        assert states[1].changes.condition.next == update_item.condition
        assert states[1].changes.condition_comment.next == update_item.condition_comment
        assert states[1].changes.purchase_date.next == update_item.purchase_date
        assert states[1].changes.group_id.next == update_item.group_id
        assert states[1].changes.tags.next == update_item.tags
        assert states[1].changes.bay_id.next == update_item.bay_id
        assert states[2].user_id == 'admin1'
        assert states[2].item_id == created_item.id
        assert states[2].comment == 'Created'
        assert states[2].changes.external_id.next == create_item.external_id
        assert states[2].changes.name.next == create_item.name
        assert states[2].changes.description.next == create_item.description
        assert states[2].changes.condition.next == create_item.condition
        assert states[2].changes.condition_comment.next == create_item.condition_comment
        assert states[2].changes.purchase_date.next == create_item.purchase_date
        assert states[2].changes.last_service.next == create_item.last_service
        assert states[2].changes.group_id.next == create_item.group_id
        assert states[2].changes.tags.next == create_item.tags
        assert states[2].changes.bay_id.next == create_item.bay_id

        resp = client.delete(
            f'/api/v1/depot/items/{created_item.id}', auth=MockAuth(sub='admin1', roles=['admin'])
        )
        assert resp.status_code == 204, resp.text

        resp = client.get('/api/v1/depot/items', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 0
