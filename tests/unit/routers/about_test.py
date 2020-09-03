from fastapi.testclient import TestClient
import pytest
from app.wdms_app import wdms_app
from app.auth.auth import require_opendes_authorized_user
from app.helper import traces

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.fixture
def client():
    yield TestClient(wdms_app)
    wdms_app.dependency_overrides = {}


@pytest.fixture
def client_with_authenticated_user():
    async def mock_require_opendes_authorized_user():
        # empty method
        pass

    client = TestClient(wdms_app)
    wdms_app.dependency_overrides[require_opendes_authorized_user] = mock_require_opendes_authorized_user
    yield client
    wdms_app.dependency_overrides = {}


def test_about_contains_build_n_version(client):

    response = client.get("/about")
    assert response.status_code == 200

    response_json = response.json()
    assert response_json['buildNumber']
    assert response_json['version']


def test_version_requires_authentication(client):
    response = client.get("/version")
    assert response.status_code == 403


def test_version_properly_read_details(client_with_authenticated_user, mocker):
    mocker.patch('app.conf.EnvVar.value', new_callable=mocker.PropertyMock, return_value='key1=value1; key2=value2')
    # all env then return the given value and so Config.build_details

    response = client_with_authenticated_user.get("/version")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json['details']['key1'] == 'value1'
    assert response_json['details']['key2'] == 'value2'
