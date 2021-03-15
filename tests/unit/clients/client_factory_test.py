# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from pytest_httpx import HTTPXMock
import httpx

from app.clients import (
    make_storage_record_client,
    make_search_client,
    StorageRecordServiceClient,
    SearchServiceClient)
from app.utils import get_or_create_ctx
from tests.unit.test_utils import make_record
import odes_storage.exceptions
import odes_search.exceptions

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

