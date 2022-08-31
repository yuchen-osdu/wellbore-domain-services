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
from typing import Optional

import pytest
from unittest import mock
from unittest.mock import patch
import asyncio
import logging
from contextlib import contextmanager

from opencensus.trace.span_context import SpanContext
from odes_storage.models import Record, StorageAcl, Legal
from starlette.routing import Mount, Router, Route

from app.model.model_utils import record_to_dict
from app.context import get_or_create_ctx

@pytest.fixture()
def ctx_fixture():
    """ Create context with a fake tracer in it """
    mock_mock = mock.MagicMock()
    mock_mock.span_context = SpanContext(trace_id="trace-id", span_id="span_id")
    ctx = get_or_create_ctx().set_current_with_value(tracer=mock_mock, logger=mock.NonCallableMock(spec_set=logging.Logger))
    yield ctx


def create_mock_class(cls_to_mock):
    cls_name = cls_to_mock.__name__ + 'AutoMock'

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    async def _async_method(cls, *args, **kwargs):
        # empty method
        pass

    @classmethod
    async def _sync_method(cls, *args, **kwargs):
        # empty method
        pass

    @classmethod
    @contextmanager
    def set_answer(cls, method_name, fn):
        previous_fn = getattr(cls, method_name)

        def _patch_sync(self_or_cls, *args, **kwargs):
            return fn(*args, **kwargs)

        async def _patch_async(self_or_cls, *args, **kwargs):
            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            return fn(*args, **kwargs)

        if asyncio.iscoroutinefunction(previous_fn):
            setattr(cls, method_name, _patch_async)
        elif callable(previous_fn):
            setattr(cls, method_name, _patch_sync)

        try:
            yield
        finally:
            setattr(cls, method_name, previous_fn)

    @classmethod
    def set_return_value(cls, method_name, return_value):
        return cls.set_answer(method_name, lambda *args, **kwargs: return_value)

    @classmethod
    def set_throw(cls, method_name, exception):
        def _do_throw(*args, **kwargs):
            raise exception
        return cls.set_answer(method_name, _do_throw)

    m_dict = {
        'set_return_value': set_return_value,
        'set_answer': set_answer,
        'set_throw': set_throw,
        '__aenter__': __aenter__,
        '__aexit__': __aexit__,
    }
    for name, _ in cls_to_mock.__dict__.items():
        if name.startswith('_'):
            continue

        attr = getattr(cls_to_mock, name)

        if asyncio.iscoroutinefunction(attr):
            m_dict[name] = _async_method
        elif callable(attr):
            m_dict[name] = _sync_method

    _new_class_ = type(cls_name, (object, ), m_dict)
    return _new_class_


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


# Format selected routes for spec generation
def format_routes(app, prefix, tags):
    for route in app.routes:
        # non selected routes are hidden
        route.include_in_schema = False
        # route path must start with prefix
        if route.path.startswith(prefix):
            # use all tags if no tag filter is provided
            if not tags:
                route.include_in_schema = True
            # otherwise route must have one of the selected tags
            elif hasattr(route,"tags"):
                if any(tag in tags for tag in route.tags):
                    # add route to the spec
                    route.include_in_schema = True
            if route.include_in_schema:
                # strip prefix from the formatted route path
                route.path_format = route.path[len(prefix):]


def side_effect_raise(*args, **kwargs):
    raise ValueError("side effect")


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
