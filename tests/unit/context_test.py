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

from app.utils import Context
import pytest
import uuid
import asyncio
import time


def get_context():
    return Context(logger='logger', correlation_id='correlation_id', request_id='request_id',
                   dev_mode=True, auth='auth', partition_id='partition_id',
                   app_key='app_key', api_key='api_key', custom1='c1', custom2='c2')


@pytest.fixture
def context_base():
    return get_context()


def test_context_repr(context_base):
    expected = '{"tracer": null, "logger": "logger", "correlation_id": "correlation_id", "request_id": "request_id", "dev_mode": true, "partition_id": "partition_id", "app_key": "app_key", "api_key": "api_key"}'

    assert str(context_base) == expected
    assert repr(context_base) == expected


def test_context_basic(context_base):
    assert context_base.logger == 'logger'
    assert context_base['logger'] == 'logger'

    assert context_base.correlation_id == 'correlation_id'
    assert context_base.request_id == 'request_id'
    assert context_base.dev_mode
    assert context_base.auth == 'auth'
    assert context_base.partition_id == 'partition_id'
    assert context_base.app_key == 'app_key'
    assert context_base.api_key == 'api_key'

    assert context_base['custom1'] == 'c1'
    assert context_base.get('custom1') == 'c1'

    assert context_base['custom2'] == 'c2'
    assert context_base.get('custom2') == 'c2'

    assert context_base.get('unknown', 'default') == 'default'

    with pytest.raises(KeyError):
        context_base['unknown']


def test_context_clone(context_base):
    new_context = context_base.with_value(correlation_id='new_correlation_id', custom1='new_c1', custom3='added_c3')

    assert new_context.logger == context_base.logger
    assert new_context.correlation_id == 'new_correlation_id'
    assert new_context.request_id == context_base.request_id
    assert new_context.dev_mode == context_base.dev_mode
    assert new_context.auth == context_base.auth
    assert new_context.partition_id == context_base.partition_id
    assert new_context.app_key == context_base.app_key
    assert new_context.api_key == context_base.api_key

    assert new_context['custom1'] == 'new_c1'
    assert new_context['custom2'] == context_base['custom2']
    assert new_context['custom3'] == 'added_c3'


async def context_assert_current_rq_id(expected_request_id):
    assert Context.current().request_id == expected_request_id


async def context_assigned_and_check():
    id = str(uuid.uuid4())
    Context.set_current(get_context().with_value(request_id=id))
    await asyncio.sleep(1)
    await context_assert_current_rq_id(id)


@pytest.mark.asyncio
async def test_set_current_with_value(context_base):
    context_base.set_current()
    Context.set_current_with_value(correlation_id='new_correlation_id')
    assert Context.current().correlation_id == 'new_correlation_id'


@pytest.mark.asyncio
async def test_context_current():
    size = 100
    coros = [context_assigned_and_check() for _ in range(size)]
    assert len(coros) == size
    await asyncio.gather(*coros)


def sync_context_assigned_and_check():
    id = str(uuid.uuid4())
    Context.set_current(get_context().with_value(request_id=id))
    time.sleep(0.01)
    assert Context.current().request_id == id


@pytest.mark.asyncio
async def test_context_current_in_thread_executor():
    size = 30
    coros = [asyncio.get_event_loop().run_in_executor(None, sync_context_assigned_and_check) for _ in range(size)]
    assert len(coros) == size
    await asyncio.gather(*coros)
