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

import asyncio
import anyio
import pytest
import time
import uuid
from anyio import to_process
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator
from opencensus.trace import tracer as open_tracer

from unittest import mock

from app.context import Context, get_headers_from_ctx


def get_context():
    # TODO app.Context  is not cleaned-up at  test teardown
    return Context(logger='logger', correlation_id='correlation_id', request_id='request_id',
                   dev_mode=True, auth='auth', partition_id='check_test_not_cleanup',
                   app_key='app_key', api_key='api_key', custom1='c1', custom2='c2',
                   x_collaboration="c_space", x_app_id="my-x-app-id")


@pytest.fixture
def context_base():
    return get_context()


def test_context_repr(context_base):
    expected = '{"tracer": null, "correlation_id": "correlation_id", "request_id": "request_id", "dev_mode": true, "partition_id": "check_test_not_cleanup", "app_key": "app_key", "api_key": "api_key", "x_user_id": null, "x_collaboration": "c_space", "x_app_id": "my-x-app-id"}'

    assert str(context_base) == expected
    assert repr(context_base) == expected


def test_context_basic(context_base):
    assert context_base.correlation_id == 'correlation_id'
    assert context_base.request_id == 'request_id'
    assert context_base.dev_mode
    assert context_base.auth == 'auth'
    assert context_base.partition_id == 'check_test_not_cleanup'
    assert context_base.app_key == 'app_key'
    assert context_base.api_key == 'api_key'
    assert context_base.x_collaboration == "c_space"
    assert context_base.x_app_id == "my-x-app-id"

    assert context_base['custom1'] == 'c1'
    assert context_base.get('custom1') == 'c1'

    assert context_base['custom2'] == 'c2'
    assert context_base.get('custom2') == 'c2'

    assert context_base.get('unknown', 'default') == 'default'

    with pytest.raises(KeyError):
        context_base['unknown']


def test_context_clone(context_base):
    new_context = context_base.with_value(correlation_id='new_correlation_id', custom1='new_c1', custom3='added_c3')

    assert new_context.correlation_id == 'new_correlation_id'
    assert new_context.request_id == context_base.request_id
    assert new_context.dev_mode == context_base.dev_mode
    assert new_context.auth == context_base.auth
    assert new_context.partition_id == context_base.partition_id
    assert new_context.app_key == context_base.app_key
    assert new_context.api_key == context_base.api_key
    assert new_context.x_collaboration == context_base.x_collaboration
    assert new_context.x_app_id == context_base.x_app_id

    assert new_context['custom1'] == 'new_c1'
    assert new_context['custom2'] == context_base['custom2']
    assert new_context['custom3'] == 'added_c3'


def context_assert_current_rq_id(expected_request_id):
    assert Context.current().request_id == expected_request_id


async def context_assigned_and_check():
    id = str(uuid.uuid4())
    Context.set_current(get_context().with_value(request_id=id))
    await anyio.sleep(1)
    context_assert_current_rq_id(id)


def test_set_current_with_value(context_base):
    context_base.set_current()
    Context.set_current_with_value(correlation_id='new_correlation_id')
    assert Context.current().correlation_id == 'new_correlation_id'


@pytest.mark.anyio
async def test_context_current():
    async with anyio.create_task_group() as tg:
        for _ in range(100):
            tg.start_soon(context_assigned_and_check)


def sync_context_assigned_and_check():
    id = str(uuid.uuid4())
    Context.set_current(get_context().with_value(request_id=id))
    time.sleep(0.01)
    assert Context.current().request_id == id


@pytest.mark.anyio
async def test_context_current_in_thread_executor_asyncio():
    size = 30
    coros = [asyncio.get_event_loop().run_in_executor(None, sync_context_assigned_and_check) for _ in range(size)]
    assert len(coros) == size
    await asyncio.gather(*coros)


@pytest.mark.anyio
async def test_context_current_in_thread_executor_anyio():
    async def foo():
        await to_process.run_sync(sync_context_assigned_and_check)

    async with anyio.create_task_group() as tg:
        for _ in range(30):
            tg.start_soon(foo)


@pytest.mark.parametrize("params, expected_result", [
    ({  # some headers are missing
         "correlation_id": None,
         "request_id": 'my-request-id',
         "auth": 'my-auth',
         "partition_id": 'my-partition-id',
         "x_user_id": None,
         "x_app_id": "my-x-app-id"},
     {
         "Authorization": "Bearer my-auth",
         "data-partition-id": "my-partition-id",
         "x-app-id": "my-x-app-id",
     }),
    ({   # all headers are here
         "correlation_id": 'my-correlation-id',
         "request_id": 'my-request-id',
         "auth": 'my-auth',
         "partition_id": 'my-partition-id',
         "x_user_id": 'my-x-user-id',
         "x_app_id": "my-x-app-id",
         "tracer": open_tracer.Tracer()
     },
     {
         "Authorization": "Bearer my-auth",
         "correlation-id": "my-correlation-id",
         "data-partition-id": "my-partition-id",
         "x-app-id": "my-x-app-id",
         "x-user-id": "my-x-user-id",
         "traceparent": "my-traceparent-value"
     }),
    ({   # only tracing headers is present
         "tracer": open_tracer.Tracer()},
     {
        'Authorization': 'Bearer None',
        'traceparent': "my-traceparent-value",
    }),
])
def test_get_headers_from_ctx(params, expected_result):
    created_ctx = Context(**params)

    with mock.patch.object(TraceContextPropagator, "to_headers", return_value={"traceparent": "my-traceparent-value"}):
        created_headers = get_headers_from_ctx(created_ctx)
        assert created_headers == expected_result
