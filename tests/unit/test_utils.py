import pytest
from tempfile import TemporaryDirectory
from odes_storage.models import Record, StorageAcl, Legal
import unittest.mock
import asyncio
from contextlib import contextmanager


def from_env(key, default=None):
    import os
    result = os.environ.get(key, default)
    # assert result, "Failed to get {} env variable".format(key)
    return result


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


def patch_async(target: str, return_value, mocker=unittest.mock):
    future = asyncio.Future()
    future.set_result(return_value)
    return mocker.patch(target, return_value=future)


def create_mock_class(cls_to_mock):
    cls_name = cls_to_mock.__name__ + 'AutoMock'

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

    m_dict = {
        'set_return_value': set_return_value,
        'set_answer': set_answer
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


def build_basic_record(kind: str = None):
    return Record(
        kind=kind or 'opendes:osdu:raw:2.0.0',
        acl=StorageAcl(viewers=['data.default.viewers@opendes.p4d.cloud.ds.com'],
                       owners=['data.default.owners@opendes.p4d.cloud.ds.com']),
        legal=Legal(),
        data={}
    )


@pytest.fixture
def basic_record(kind: str = None):
    return build_basic_record(kind)


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