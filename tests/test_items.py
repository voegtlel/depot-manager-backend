from datetime import date, timedelta

from fastapi.testclient import TestClient

from depot_server.api import app
from depot_server.api.auth import Authentication
from depot_server.model import ItemInWrite, Item, ItemCondition, ItemState, BayInWrite, Bay
from tests.db_helper import clear_all
from tests.mock_auth import MockAuthentication, MockAuth


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

        create_item = ItemInWrite(
            external_id='item_1',
            name="Item 1",
            description="First Item",
            condition=ItemCondition.Good,
            condition_comment="Very Good",
            purchase_date=date.today(),
            last_service=date.today(),
            picture_id=None,
            group_id='item_group_1',
            tags=['item', 'one'],
            bay_id=created_bay_1.id,
            change_comment="Created",
        )
        resp = client.post(
            '/api/v1/depot/items', data=create_item.json(), auth=MockAuth(sub='admin1', roles=['admin']),
        )
        assert resp.status_code == 201, resp.text
        created_item = Item.validate(resp.json())
        assert created_item.dict(exclude={'id'}) == create_item.dict(exclude={'change_comment'})

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
            last_service=date.today() + timedelta(days=2),
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
        assert updated_item.dict(exclude={'id'}) == update_item.dict(exclude={'change_comment'})

        resp = client.get(f'/api/v1/depot/items/{created_item.id}/history', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        states = [ItemState.validate(r) for r in resp.json()]
        assert len(states) == 2
        assert states[0].user_id == 'admin2'
        assert states[0].item_id == created_item.id
        assert states[0].comment == 'Updated'
        assert states[0].changes.external_id.next == update_item.external_id
        assert states[0].changes.name.next == update_item.name
        assert states[0].changes.description.next == update_item.description
        assert states[0].changes.condition.next == update_item.condition
        assert states[0].changes.condition_comment.next == update_item.condition_comment
        assert states[0].changes.purchase_date.next == update_item.purchase_date
        assert states[0].changes.last_service.next == update_item.last_service
        assert states[0].changes.group_id.next == update_item.group_id
        assert states[0].changes.tags.next == update_item.tags
        assert states[0].changes.bay_id.next == update_item.bay_id
        assert states[1].user_id == 'admin1'
        assert states[1].item_id == created_item.id
        assert states[1].comment == 'Created'
        assert states[1].changes.external_id.next == create_item.external_id
        assert states[1].changes.name.next == create_item.name
        assert states[1].changes.description.next == create_item.description
        assert states[1].changes.condition.next == create_item.condition
        assert states[1].changes.condition_comment.next == create_item.condition_comment
        assert states[1].changes.purchase_date.next == create_item.purchase_date
        assert states[1].changes.last_service.next == create_item.last_service
        assert states[1].changes.group_id.next == create_item.group_id
        assert states[1].changes.tags.next == create_item.tags
        assert states[1].changes.bay_id.next == create_item.bay_id

        resp = client.delete(
            f'/api/v1/depot/items/{created_item.id}', auth=MockAuth(sub='admin1', roles=['admin'])
        )
        assert resp.status_code == 200, resp.text

        resp = client.get('/api/v1/depot/items', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 0
