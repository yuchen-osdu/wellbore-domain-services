from fastapi.testclient import TestClient
import pytest
from app.wdms_app import wdms_app, wellbore_api_group_prefix
from app.auth.auth import require_opendes_authorized_user
from app.helper import traces
from app.conf import Config
from tests.unit.test_utils import ctx_fixture

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.fixture
def client(ctx_fixture):
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


def build_url(path: str):
    return wellbore_api_group_prefix + path


def test_about_contains_build_n_version(client):

    response = client.get(build_url("/about"))
    assert response.status_code == 200

    response_json = response.json()
    assert response_json['buildNumber']
    assert response_json['version']


@pytest.mark.parametrize("cloud_provider", ['Azure', 'gcp', 'unknown', None])
def test_about_with_cloud_provider(client, cloud_provider):

    Config.cloud_provider.value = cloud_provider

    response = client.get(build_url("/about"))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['cloudEnvironment'] == cloud_provider


def test_version_requires_authentication(client):
    response = client.get(build_url("/version"))
    assert response.status_code == 403


def test_version_properly_read_details(client_with_authenticated_user, monkeypatch):
    # override value of build details
    Config.build_details.value = 'key1=value1; key2=value2'

    response = client_with_authenticated_user.get(build_url("/version"))
    assert response.status_code == 200
    response_json = response.json()
    assert response_json['details']['key1'] == 'value1'
    assert response_json['details']['key2'] == 'value2'
