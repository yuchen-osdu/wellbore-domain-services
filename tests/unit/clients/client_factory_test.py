import pytest
from pytest_httpx import HTTPXMock
import httpx

from app.clients import (
    make_storage_record_client,
    make_search_client,
    make_entitlements_auth_client,
    StorageRecordServiceClient,
    SearchServiceClient,
    EntitlementsAuthServiceClient)
from app.utils import get_or_create_ctx
from tests.unit.test_utils import make_record
import odes_storage.exceptions
import odes_search.exceptions
import odes_entitlements.exceptions
from tests.unit.test_utils import ctx_fixture as test_context


@pytest.mark.asyncio
async def test_make_storage_client(httpx_mock: HTTPXMock, test_context):
    host = 'http://my_host:81234'
    async with make_storage_record_client(host) as client:
        assert isinstance(client, StorageRecordServiceClient)

        # ensure host
        assert client.api_client.host == host
        # using literal here to make config change visible
        assert client.api_client._async_client.timeout == httpx.Timeout(timeout=45)

        httpx_mock.add_response(status_code=500)

        # expect the correct exception - ie. composition do not mix several clients
        with pytest.raises(odes_storage.exceptions.UnexpectedResponse):
            await client.create_or_update_records(data_partition_id="dp", record=[make_record(id='123')])


@pytest.mark.asyncio
async def test_make_search_client(httpx_mock: HTTPXMock, test_context):
    host = 'http://my_host:81234'
    async with make_search_client(host) as client:
        assert isinstance(client, SearchServiceClient)

        # ensure host
        assert client.api_client.host == host
        assert client.api_client._async_client.timeout == httpx.Timeout(timeout=45)
        get_or_create_ctx()

        httpx_mock.add_response(status_code=500)

        # expect the correct exception - ie. composition do not mix several clients
        with pytest.raises(odes_search.exceptions.UnexpectedResponse):
            await client.get_index_schema(kind='kind', data_partition_id="dp")


@pytest.mark.asyncio
async def test_make_entitlement_client(httpx_mock: HTTPXMock, test_context):
    host = 'http://my_host:81234'
    async with make_entitlements_auth_client(host) as client:
        assert isinstance(client, EntitlementsAuthServiceClient)

        # ensure host
        assert client.api_client.host == host
        assert client.api_client._async_client.timeout == httpx.Timeout(timeout=45)
        get_or_create_ctx()

        httpx_mock.add_response(status_code=500)

        # expect the correct exception - ie. composition do not mix several clients
        with pytest.raises(odes_entitlements.exceptions.UnexpectedResponse):
            await client.auth()
