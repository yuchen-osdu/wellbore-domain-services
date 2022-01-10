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
import mock
import asyncio
from tempfile import TemporaryDirectory
from opencensus.trace.span_context import SpanContext
from contextlib import contextmanager

from odes_storage.models import Record, StorageAcl, Legal

from app.model.model_utils import record_to_dict
from app.utils import get_or_create_ctx

@pytest.fixture()
def ctx_fixture():
    """ Create context with a fake tracer in it """
    mock_mock = mock.MagicMock()
    mock_mock.span_context = SpanContext(trace_id="trace-id", span_id="span_id")
    ctx = get_or_create_ctx().set_current_with_value(tracer=mock_mock, logger=NopeLogger())
    yield ctx


@pytest.fixture
def nope_logger_fixture():
    nope_logger()
    yield

def nope_logger():
    from app.helper import logger
    logger._LOGGER = NopeLogger()

class NopeLogger:
    def __init__(self):
        # empty method
        pass

    def debug(*arg, **kargs):
        # empty method
        pass

    def info(*arg, **kargs):
        # empty method
        pass

    def warning(*arg, **kargs):
        # empty method
        pass

    def error(*arg, **kargs):
        # empty method
        pass

    def exception(*arg, **kargs):
        # empty method
        pass

    def critical(*arg, **kargs):
        # empty method
        pass

    def log(*arg, **kargs):
        # empty method
        pass


class AsyncMock:
    def __init__(self, *, return_value=None, forward_input_name: str = None, forward_input_index: int = 0):
        self._return_value = return_value
        self._from_input = forward_input_name
        self._from_input_index = forward_input_index

    async def __call__(self, *args, **kwargs):
        if self._return_value is not None:
            return self._return_value

        if self._from_input:
            return kwargs[self._from_input]

        if self._from_input_index < 0:
            return None

        return args[self._from_input_index]


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


def assert_dict_contained(dict_to_check: dict, ref_dict: dict, path=''):
    """
    check actual dict contained ref_dict
    path param use the default value
    """
    for key, value in ref_dict.items():
        current_path = path + '.' + key if path else key
        assert key in dict_to_check
        sub_item = dict_to_check[key]
        assert type(sub_item) == type(value), f'type of {current_path} ({type(sub_item)}) != ref {type(value)}'
        if type(value) == dict:
            assert_dict_contained(sub_item, value, current_path)
        else:
            assert sub_item == value, f'{current_path}: actual {sub_item} != ref {value}'


@pytest.fixture
async def temp_directory() -> str:
    with TemporaryDirectory() as tmpdir:
        yield tmpdir


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


def make_fn_return_value(value_to_return, as_coroutine: bool = False):
    if not as_coroutine:
        return lambda *args, **kwargs: value_to_return

    async def return_async_fn(*args, **kwargs):
        return value_to_return

    return return_async_fn


def make_fn_do_nothing(as_coroutine: bool = False):
    return make_fn_return_value(None, as_coroutine)


def make_async_return_value(value_to_return):
    return make_fn_return_value(value_to_return, True)


def make_async_do_nothing():
    return make_fn_do_nothing(True)



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
                    # strip prefix from the formatted route path
                    route.path_format = route.path.removeprefix(prefix)


def side_effect_raise(*args, **kwargs):
    raise ValueError("side effect")
