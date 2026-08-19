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
import logging
from typing import Optional
from unittest import mock

from odes_storage.models import Legal, Record, StorageAcl
from osdu.core.api.storage.tenant import Tenant
import pytest
from starlette.routing import Mount, Route, Router

from app.context import get_or_create_ctx
from app.injector.app_injector import AppInjector
from app.model.model_utils import record_to_dict


@pytest.fixture()
def ctx_fixture():
    """ Create context with a fake tracer in it """
    mock_mock = mock.MagicMock()

    ctx = get_or_create_ctx()
    fake_tenant = Tenant(data_partition_id=ctx.partition_id or 'test_partition',
                         project_id='test_project',
                         credentials='',
                         bucket_name='test_bucket')
    ctx = ctx.set_current_with_value(
        tracer=mock_mock,
        logger=mock.NonCallableMock(spec_set=logging.Logger),
        app_injector=ctx.app_injector or AppInjector(),
        partition_id=ctx.partition_id or 'test_partition',
        tenant=ctx.tenant or fake_tenant
    )
    return ctx


def make_record(as_dict=False, **kwargs):
    kwargs.setdefault('kind', 'opendes:osdu:raw:2.0.0')
    kwargs.setdefault('acl', StorageAcl(
        viewers=['data.default.viewers@opendes.p4d.cloud.ds.com'],
        owners=['data.default.owners@opendes.p4d.cloud.ds.com']))
    kwargs.setdefault('legal', Legal())
    kwargs.setdefault('data', {})
    record = Record(**kwargs)
    return record_to_dict(record) if as_dict else record


@pytest.fixture
def basic_record(kind: str = None):
    return make_record() if kind is None else make_record(kind=kind)


def gen_all_routes_request(rtr: Router, prefix: Optional[str] = None):
    if prefix is None:
        prefix = ""

    for route in rtr.routes:
        if isinstance(route, Mount):
            # if this is a Mount, we need to recurse on the route
            yield from gen_all_routes_request(route.app, route.path)
        elif isinstance(route, Route):
            for method in route.methods:
                yield method, prefix + route.path
        else:
            RuntimeError(f"{route} routes retrieval not implemented")
