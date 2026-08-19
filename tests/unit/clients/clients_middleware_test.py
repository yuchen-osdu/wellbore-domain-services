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
from app.clients import make_storage_record_client, make_search_client
from app.context import Context

from tests.unit.test_utils import ctx_fixture


@pytest.fixture
def headers_data():
    return [
        # context attribute name, header name, value
        ("x_collaboration", "x-collaboration", "some_collaboration_space"),
        ("correlation_id", "correlation-id", "some-correlation-id"),
        ("x_user_id", "x-user-id", "some-user-id"),
    ]


@pytest.fixture
def context(ctx_fixture, nope_logger_fixture, headers_data):
    # safety: make sure no methods on tracer have been called yet
    assert ctx_fixture.tracer.method_calls == []
    return ctx_fixture.set_current_with_value(
        auth="foobar",
        **{v[0]: v[2] for v in headers_data}
    )


@pytest.fixture
def expected_headers(headers_data):
    return {v[1]: v[2] for v in headers_data}


@pytest.mark.anyio
async def test_fwd_headers_to_outgoing_request_to_storage(local_dev_config,
                                                          context: Context,
                                                          expected_headers,
                                                          httpx_mock: HTTPXMock):
    async with make_storage_record_client(host=local_dev_config.service_host_search.value,
                                          timeout=local_dev_config.de_client_config_timeout.value) as storage_client:
        httpx_mock.add_response(match_headers=expected_headers)
        # force to use endpoint which does not return a response to skip model validation
        response = await storage_client.delete_record(id="123", data_partition_id="test")
        assert response is not None


@pytest.mark.anyio
async def test_fwd_headers_to_outgoing_request_to_search(local_dev_config,
                                                         context: Context,
                                                         expected_headers,
                                                         httpx_mock: HTTPXMock):
    async with make_search_client(host=local_dev_config.service_host_search.value,
                                  timeout=local_dev_config.de_client_config_timeout.value) as search_client:

        httpx_mock.add_response(match_headers=expected_headers)
        # force to use endpoint which does not return a response to skip model validation
        response = await search_client.delete_index(kind="kind", data_partition_id="test")
        assert response is not None
