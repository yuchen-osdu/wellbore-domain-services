import httpx
import pytest
from pytest_httpx import HTTPXMock, to_response

from app.clients import make_storage_record_client, make_search_client

from tests.unit.test_utils import ctx_fixture
import app.conf as conf
from app.helper import traces
from app.auth.auth import require_opendes_authorized_user
from app.middleware import require_data_partition_id
from app.injector.main_injector import MainInjector


@pytest.mark.asyncio
async def test_fwd_correlation_id_to_outgoing_request_to_storage(httpx_mock: HTTPXMock, ctx_fixture):
    storage_url = "http://example.com"  # well formed url required
    expected_correlation_id = 'some-correlation-id'

    async with make_storage_record_client(storage_url) as storage_client:
        httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})

        ctx_fixture.set_current_with_value(correlation_id=expected_correlation_id)

        # force to use endpoint which does not return a response to skip model validation
        response = await storage_client.delete_record(id="123", data_partition_id="test")
        assert response is not None


@pytest.mark.asyncio
async def test_fwd_correlation_id_to_outgoing_request_to_search(httpx_mock: HTTPXMock, ctx_fixture):
    storage_url = "http://example.com"  # well formed url required
    expected_correlation_id = 'some-correlation-id'

    async with make_search_client(storage_url) as search_client:
        httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})

        ctx_fixture.set_current_with_value(correlation_id=expected_correlation_id)

        # force to use endpoint which does not return a response to skip model validation
        response = await search_client.delete_index(kind="kind", data_partition_id="test")
        assert response is not None


@pytest.fixture()
async def wdms_app_mocked():

    from fastapi.testclient import TestClient
    from app.wdms_app import wdms_app, app_injector
    from app.clients import StorageRecordServiceClient

    conf.Config.service_host_search.value = "http://localhost:8888"
    conf.Config.service_host_storage.value = "http://localhost:9999"

    wdms_app.dependency_overrides[require_opendes_authorized_user] = lambda: True
    wdms_app.dependency_overrides[require_data_partition_id] = lambda: True
    wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')
    client = TestClient(wdms_app)

    MainInjector().configure(app_injector)

    yield client

    wdms_app.dependency_overrides = {}

    # explicit close client in teardown
    storage_client = await app_injector.get(StorageRecordServiceClient)
    if storage_client is not None:
        await storage_client.api_client.close()


def test_outgoing_tracing_headers_with_incoming_headers(wdms_app_mocked, httpx_mock):

    version = '00'
    trace_id = '80f22fa582f64d2584e76b4aac231f12'
    span_id = '7f522a92333490ec'
    trace_options = '01'

    input_headers = {
        'traceparent': f'{version}-{trace_id}-{span_id}-{trace_options}'
    }

    def custom_response(request: httpx.Request, *args, **kwargs):
        assert request.headers['traceparent'], "check if tracing header is present"

        outgoing_context = traces.get_trace_propagator().from_headers(request.headers)
        assert trace_id == outgoing_context.trace_id, "check trace id is the same than input one"
        assert outgoing_context.span_id
        assert outgoing_context.trace_options.enabled

        return to_response(
            json={"url": str(request.url)},
        )

    httpx_mock.add_callback(custom_response)

    response = wdms_app_mocked.delete(f'/ddms/v2/logs/123456', headers=input_headers)
    assert response.status_code == 204


def test_outgoing_tracing_headers_without_headers(wdms_app_mocked, httpx_mock):

    def custom_response(request: httpx.Request, *args, **kwargs):
        assert request.headers['traceparent'], "check if tracing header is present"

        outgoing_context = traces.get_trace_propagator().from_headers(request.headers)
        assert outgoing_context.trace_id, "check trace id exists"
        assert outgoing_context.span_id, "check span id exists"
        assert outgoing_context.trace_options.enabled

        return to_response(
            json={"url": str(request.url)},
        )

    httpx_mock.add_callback(custom_response)

    response = wdms_app_mocked.delete('/ddms/v2/logs/123456')
    assert response.status_code == 204
