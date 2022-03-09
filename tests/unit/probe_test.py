import pytest
from fastapi.testclient import TestClient
from app.wdms_app import wdms_app
from tests.unit.test_utils import ctx_fixture
from app.helper import traces
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

@pytest.fixture
def client(ctx_fixture, nope_logger_fixture):
    yield TestClient(wdms_app)
    wdms_app.dependency_overrides = {}

@pytest.mark.parametrize("probe_url", [('/readiness'),('/healthz'),])
def test_readiness_probe(client, probe_url):
    response = client.get(probe_url)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json == {'status': 'healthy'}



