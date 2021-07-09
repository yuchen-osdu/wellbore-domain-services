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
from app.utils import Context, get_or_create_ctx

from tests.unit.test_utils import ctx_fixture

@pytest.mark.asyncio
async def test_fwd_correlation_id_to_outgoing_request_to_storage(ctx_fixture: Context, httpx_mock: HTTPXMock):
    storage_url = "http://example.com"  # well formed url required
    expected_correlation_id = 'some-correlation-id'

    ctx = ctx_fixture.with_correlation_id(expected_correlation_id).with_auth("foobar")
    Context.set_current(ctx)

    # safety: make sure no methods on tracer have been called yet
    assert ctx.tracer.method_calls == []

    async with make_storage_record_client(storage_url) as storage_client:
        httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})
        # force to use endpoint which does not return a response to skip model validation
        response = await storage_client.delete_record(id="123", data_partition_id="test")
        assert response is not None

    # make sure correlation-id is traced when doing a request to storage
    ctx.tracer.add_attribute_to_current_span.assert_any_call(
        attribute_key='correlation-id',
        attribute_value=expected_correlation_id
    )

@pytest.mark.asyncio
async def test_fwd_correlation_id_to_outgoing_request_to_search(ctx_fixture: Context, httpx_mock: HTTPXMock):
    storage_url = "http://example.com"  # well formed url required
    expected_correlation_id = 'some-correlation-id'

    ctx = ctx_fixture.with_correlation_id(expected_correlation_id).with_auth("foobar")
    Context.set_current(ctx)

    # safety: make sure no methods on tracer have been called yet
    assert ctx.tracer.method_calls == []

    async with make_search_client(storage_url) as search_client:
        httpx_mock.add_response(match_headers={'correlation-id': expected_correlation_id})
        # force to use endpoint which does not return a response to skip model validation
        response = await search_client.delete_index(kind="kind", data_partition_id="test")
        assert response is not None
    
    # make sure correlation-id is traced when doing a request to search
    ctx.tracer.add_attribute_to_current_span.assert_any_call(
        attribute_key='correlation-id',
        attribute_value=expected_correlation_id
    )
