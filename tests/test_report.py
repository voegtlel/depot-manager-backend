from fastapi.testclient import TestClient
from requests import Session
from typing import Tuple

from depot_server.api import app
from depot_server.api.auth import Authentication
from depot_server.model import ReportElementInWrite, ReportElement, ReportProfileInWrite, ReportProfile
from tests.db_helper import clear_all
from tests.mock_auth import MockAuthentication, MockAuth


def _create_report_profile(client: Session) -> Tuple[ReportProfile, Tuple[ReportElement, ReportElement]]:
    create_report_element_1 = ReportElementInWrite(title="Rep1", description="Desc1")
    create_report_element_2 = ReportElementInWrite(title="Rep2", description="Desc2")
    create_report_element_3 = ReportElementInWrite(title="Rep3", description="Desc3")
    resp = client.post(
        '/api/v1/depot/report-elements', data=create_report_element_1.json(),
        auth=MockAuth(sub='admin1', roles=['admin']),
    )
    assert resp.status_code == 201, resp.text
    created_report_element_1 = ReportElement.validate(resp.json())
    assert ReportElementInWrite.validate(created_report_element_1) == create_report_element_1

    resp = client.post(
        '/api/v1/depot/report-elements', data=create_report_element_2.json(),
        auth=MockAuth(sub='admin1', roles=['admin']),
    )
    assert resp.status_code == 201, resp.text
    created_report_element_2 = ReportElement.validate(resp.json())
    assert ReportElementInWrite.validate(created_report_element_2) == create_report_element_2

    resp = client.post(
        '/api/v1/depot/report-elements', data=create_report_element_3.json(),
        auth=MockAuth(sub='admin1', roles=['admin']),
    )
    assert resp.status_code == 201, resp.text
    created_report_element_3 = ReportElement.validate(resp.json())
    assert ReportElementInWrite.validate(created_report_element_3) == create_report_element_3

    create_report_profile = ReportProfileInWrite(
        title="Prof1",
        description="ProfileDesc1",
        elements=[created_report_element_1.id, created_report_element_3.id],
    )
    resp = client.post(
        '/api/v1/depot/report-profiles', data=create_report_profile.json(),
        auth=MockAuth(sub='admin1', roles=['admin']),
    )
    assert resp.status_code == 201, resp.text
    created_report_profile = ReportProfile.validate(resp.json())
    assert ReportProfileInWrite.validate(created_report_profile) == create_report_profile

    return created_report_profile, (created_report_element_1, created_report_element_3)


def test_report(monkeypatch, motor_mock):
    monkeypatch.setattr(Authentication, '__call__', MockAuthentication.__call__)

    with TestClient(app) as client:
        clear_all()

        _create_report_profile(client)
