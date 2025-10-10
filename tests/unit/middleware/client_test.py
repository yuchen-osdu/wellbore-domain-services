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
