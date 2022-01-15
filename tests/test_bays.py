from fastapi.testclient import TestClient

from depot_server.api import app
from depot_server.helper.auth import Authentication
from depot_server.model import BayInWrite, Bay
from tests.db_helper import clear_all
from tests.mock_auth import MockAuthentication, MockAuth


def test_bay(monkeypatch, motor_mock):
    monkeypatch.setattr(Authentication, '__call__', MockAuthentication.__call__)

    with TestClient(app) as client:
        clear_all()

        create_bay = BayInWrite(external_id='bay_1', name="Bay 1", description="Top Left")
        resp = client.post(
            '/api/v1/depot/bays', data=create_bay.json(), auth=MockAuth(sub='admin1', roles=['admin']),
        )
        assert resp.status_code == 201, resp.text
        created_bay = Bay.validate(resp.json())
        assert BayInWrite.validate(created_bay) == create_bay

        resp = client.get('/api/v1/depot/bays', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        bays = [Bay.validate(b) for b in resp.json()]
        assert len(bays) == 1
        assert bays[0] == created_bay

        resp = client.get(f'/api/v1/depot/bays/{created_bay.id}', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        assert Bay.validate(resp.json()) == created_bay

        update_bay = BayInWrite(external_id='bay_1_upd', name="Bay 1 Upd", description="Top Right")
        resp = client.put(
            f'/api/v1/depot/bays/{created_bay.id}', data=update_bay.json(), auth=MockAuth(sub='admin1', roles=['admin'])
        )
        assert resp.status_code == 200, resp.text
        updated_bay = Bay.validate(resp.json())
        assert BayInWrite.validate(updated_bay) == update_bay

        resp = client.delete(
            f'/api/v1/depot/bays/{created_bay.id}', auth=MockAuth(sub='admin1', roles=['admin'])
        )
        assert resp.status_code == 204, resp.text

        resp = client.get('/api/v1/depot/bays', auth=MockAuth(sub='user1'))
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 0
