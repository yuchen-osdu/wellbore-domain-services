import pytest
from pytest_httpx import HTTPXMock
from app.clients import make_storage_record_client, make_search_client
from app.utils import Context, get_or_create_ctx

from tests.unit.test_utils import ctx_fixture, nope_logger_fixture

@pytest.mark.asyncio
async def test_fwd_correlation_id_to_outgoing_request_to_storage(ctx_fixture, httpx_mock: HTTPXMock):
    storage_url = "http://example.com"  # well formed url required
    expected_correlation_id = 'some-correlation-id'

    storage_client = make_storage_record_client(storage_url)
    httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})

    ctx = ctx_fixture.with_correlation_id(expected_correlation_id).with_auth("foobar")
    Context.set_current(ctx)

    # force to use endpoint which does not return a response to skip model validation
    response = await storage_client.delete_record(id="123", data_partition_id="test")
    assert response is not None


@pytest.mark.asyncio
async def test_fwd_correlation_id_to_outgoing_request_to_search(httpx_mock: HTTPXMock):
    storage_url = "http://example.com"  # well formed url required
    expected_correlation_id = 'some-correlation-id'

    search_client = make_search_client(storage_url)
    httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})

    ctx = get_or_create_ctx().with_correlation_id(expected_correlation_id).with_auth("foobar")
    Context.set_current(ctx)

    # force to use endpoint which does not return a response to skip model validation
    response = await search_client.delete_index(kind="kind", data_partition_id="test")
    assert response is not None
