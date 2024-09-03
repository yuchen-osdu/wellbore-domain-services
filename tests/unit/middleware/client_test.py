import httpx
import pytest
from pytest_httpx import HTTPXMock

from opentelemetry import trace
from opentelemetry.trace import TraceFlags, SpanKind
from tests.unit.middleware.traces_middleware_test import ExporterInTest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace import TracerProvider

from app.clients import make_storage_record_client, make_search_client
from tests.unit.test_utils import ctx_fixture
from tests.unit.fixtures import TEST_CLIENT_HOST


@pytest.mark.anyio
async def test_fwd_correlation_id_to_outgoing_request_to_storage(local_dev_config,
                                                                 httpx_mock: HTTPXMock,
                                                                 ctx_fixture,
                                                                 nope_logger_fixture):
    expected_correlation_id = 'some-correlation-id'

    async with make_storage_record_client(host=local_dev_config.service_host_storage.value,
                                          timeout=local_dev_config.de_client_config_timeout.value) as storage_client:
        httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})

        ctx_fixture.set_current_with_value(correlation_id=expected_correlation_id)

        # force to use endpoint which does not return a response to skip model validation
        response = await storage_client.delete_record(id="123", data_partition_id="test")
        assert response is not None


@pytest.mark.anyio
async def test_fwd_correlation_id_to_outgoing_request_to_search(local_dev_config,
                                                                httpx_mock: HTTPXMock,
                                                                ctx_fixture,
                                                                nope_logger_fixture):
    expected_correlation_id = 'some-correlation-id'

    async with make_search_client(host=local_dev_config.service_host_search.value,
                                  timeout=local_dev_config.de_client_config_timeout.value) as search_client:
        httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})

        ctx_fixture.set_current_with_value(correlation_id=expected_correlation_id)

        # force to use endpoint which does not return a response to skip model validation
        response = await search_client.delete_index(kind="kind", data_partition_id="test")
        assert response is not None


def _add_testing_span_exporter():
    """ Retrieve tracer and add the testing span Exporter to verify created spans """
    provider: TracerProvider = trace.get_tracer_provider()
    exporter = ExporterInTest()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    return exporter


@pytest.fixture
def non_mocked_hosts() -> list:
    """ fixture to prevent pytest-httpx from mocking requests to the wdms app under test
    """
    return [TEST_CLIENT_HOST]


@pytest.mark.anyio
@pytest.mark.parametrize("existing_tracing_context", [True, False])
async def test_client_tracing_middleware(local_dev_config,
                                         app_configurable_with_testclient,
                                         httpx_mock: HTTPXMock,
                                         existing_tracing_context):

    app, client = app_configurable_with_testclient(
        storage_client_mock=make_storage_record_client(host=local_dev_config.service_host_storage.value,
                                                       timeout=local_dev_config.de_client_config_timeout.value),
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True
    )
    exporter = _add_testing_span_exporter()

    if existing_tracing_context:
        version = '00'
        trace_id = '80f22fa582f64d2584e76b4aac231f12'
        span_id = '7f522a92333490ec'
        trace_options = '01'
        input_headers = {'traceparent': f'{version}-{trace_id}-{span_id}-{trace_options}'}
    else:
        input_headers = {}

    def _custom_response(request: httpx.Request, *args, **kwargs):
        if existing_tracing_context:
            assert trace_id in request.headers['traceparent']
        return httpx.Response(status_code=204, json={"url": str(request.url)})

    httpx_mock.add_callback(
        _custom_response,
        method="POST",
        url="https://test-endpoint/api/storage/v2/records/123456:delete"
    )

    response = await client.delete('/ddms/v2/logs/123456', headers=input_headers)
    assert response.status_code == 204
    assert len(exporter.exported) == 2
    parent_span = exporter.exported[1]
    storage_dependency_span = exporter.exported[0]

    if not existing_tracing_context:
        assert parent_span.parent is None

    assert storage_dependency_span.context.trace_id == parent_span.context.trace_id
    assert storage_dependency_span.context.trace_flags == TraceFlags.SAMPLED
    assert storage_dependency_span.kind == SpanKind.CLIENT

    storage_span_attributes = storage_dependency_span.attributes
    assert storage_span_attributes['http.host'] == 'test-endpoint'
    assert storage_span_attributes['http.method'] == 'POST'
    assert storage_span_attributes['http.route'] == '/api/storage/v2/records/123456:delete'
    assert storage_span_attributes['http.url'] == 'https://test-endpoint/api/storage/v2/records/123456:delete'

    assert len(storage_span_attributes['correlation-id']) == 36
    assert storage_span_attributes['http.status_code'] == 204
