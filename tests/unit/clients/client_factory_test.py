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

import httpx
from unittest import mock
import pytest
from pytest_httpx import HTTPXMock
from httpx import (RemoteProtocolError, TimeoutException)

import odes_search.exceptions
import odes_storage.exceptions

from app.clients import (
    make_storage_record_client,
    make_search_client,
    StorageRecordServiceClient,
    SearchServiceClient)
from app.clients.backoff_policy import backoff_policy, _exceptions_type_to_retry

from app.context import get_or_create_ctx
from tests.unit.test_utils import make_record
from odes_storage.exceptions import ResponseHandlingException
from app.conf import Config

from tests.unit.test_utils import ctx_fixture

@pytest.mark.asyncio
async def test_make_storage_client(local_dev_config, httpx_mock: HTTPXMock, ctx_fixture):
    async with make_storage_record_client(host=local_dev_config.service_host_storage.value,
                                          timeout=local_dev_config.de_client_config_timeout.value) as client:
        assert isinstance(client, StorageRecordServiceClient)

        # ensure host
        assert client.api_client.host == local_dev_config.service_host_storage.value
        # using literal here to make config change visible
        assert client.api_client._async_client.timeout == httpx.Timeout(timeout=10)

        httpx_mock.add_response(status_code=500)

        # expect the correct exception - ie. composition do not mix several clients
        with pytest.raises(odes_storage.exceptions.UnexpectedResponse):
            await client.create_or_update_records(data_partition_id="dp", record=[make_record(id='123')])


@pytest.mark.asyncio
async def test_make_search_client(local_dev_config, httpx_mock: HTTPXMock, ctx_fixture):
    async with make_search_client(host=local_dev_config.service_host_search.value,
                                  timeout=local_dev_config.de_client_config_timeout.value) as client:
        assert isinstance(client, SearchServiceClient)

        # ensure host
        assert client.api_client.host == local_dev_config.service_host_search.value
        assert client.api_client._async_client.timeout == httpx.Timeout(timeout=10)
        get_or_create_ctx()

        httpx_mock.add_response(status_code=500)

        # expect the correct exception - ie. composition do not mix several clients
        with pytest.raises(odes_search.exceptions.UnexpectedResponse):
            await client.get_index_schema(kind='kind', data_partition_id="dp")


class MyException(Exception):
    pass


@pytest.mark.parametrize("exception_type, requested_retries_count", [
    (RemoteProtocolError, 3),
    (TimeoutException, 4),
    (ResponseHandlingException, 2),
    (RuntimeError, 4),
    (MyException, 4),
])
def test_de_clients_backoff(exception_type, requested_retries_count):
    """
        Ensure retry mechanism is based on config 'de_client_backoff_max_tries' value and
        only specific Exceptions type trigger this retry.
    """

    # assigned expected retries count to config, to be used by backoff decorator
    Config.de_client_backoff_max_tries.value = requested_retries_count

    mocky_func = mock.MagicMock(autospec=True, side_effect=exception_type(f'{exception_type} has raised!'))
    mocky_func.__name__ = ''

    decorator_func = backoff_policy()
    decorated_mocked_func = decorator_func(mocky_func)
    try:
        decorated_mocked_func()
    except BaseException:
        # consume exception to let the test case pass
        pass
    finally:
        retries_count = requested_retries_count if exception_type in _exceptions_type_to_retry else 1
        assert mocky_func.call_count == retries_count
