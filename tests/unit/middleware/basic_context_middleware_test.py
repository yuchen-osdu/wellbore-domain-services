import pytest
from unittest.mock import Mock, PropertyMock

from app import wdms_app
from app.middleware.basic_context_middleware import CreateBasicContextMiddleware
from app.context import Context
from starlette.datastructures import URL


def test_ensure_basic_context_middleware_is_first():
    assert wdms_app.wdms_app.user_middleware[0].cls is CreateBasicContextMiddleware


@pytest.mark.asyncio
async def test_should_start_and_leave_cleared_context(local_dev_config):
    middleware = CreateBasicContextMiddleware(config=local_dev_config, injector=None, app=None)
    request_mock = Mock()
    type(request_mock).headers = PropertyMock(return_value={})
    type(request_mock).scope = PropertyMock(return_value={})
    type(request_mock).url = PropertyMock(return_value=URL())

    properties_to_check = [
        'tracer', 'logger', 'correlation_id', 'request_id', 'dev_mode', 'auth', 'partition_id',
        'app_key', 'api_key', 'user', 'app_injector', 'x_user_id']

    # GIVEN set current with values and request with no headers
    Context(**{v: v for v in properties_to_check}).set_current()

    # check current contains values
    previous_ctx = Context.current()
    assert all((previous_ctx[p] == p for p in properties_to_check))

    async def check_context_values_are_none_then_set(*args, **kwargs):
        ctx = Context.current()
        assert all((
            ctx[p] is None or ctx[p] != previous_ctx[p]  # some are defaulted (e.g. correlation_id)
            for p in properties_to_check))

        # put some values
        Context.set_current_with_value(**{v: 'new values' for v in properties_to_check})

        # ensure current have those new values
        ctx = Context.current()
        assert all((ctx[p] == 'new values' for p in properties_to_check))

        return None

    # WHEN middleware called, THEN values in current context are none
    await middleware.dispatch(request_mock, check_context_values_are_none_then_set)

    # and THEN context values should be back to none
    after_ctx = Context.current()
    assert all((after_ctx[p] is None for p in properties_to_check))


@pytest.mark.asyncio
async def test_should_leave_cleared_context_in_case_of_exception(local_dev_config):
    middleware = CreateBasicContextMiddleware(config=local_dev_config, injector=None, app=None)
    request_mock = Mock()
    type(request_mock).headers = PropertyMock(return_value={})
    type(request_mock).scope = PropertyMock(return_value={})
    type(request_mock).url = PropertyMock(return_value=URL())

    properties_to_check = [
        'tracer', 'logger', 'correlation_id', 'request_id', 'dev_mode', 'auth', 'partition_id',
        'app_key', 'api_key', 'user', 'app_injector', 'x_user_id']

    # GIVEN set current with values and request with no headers
    Context(**{v: v for v in properties_to_check}).set_current()

    async def call_next_that_throw(*args, **kwargs):
        raise ValueError()

    # WHEN middleware called with an inner failing call
    with pytest.raises(ValueError):
        await middleware.dispatch(request_mock, call_next_that_throw)

    # and THEN context values should be back to none
    after_ctx = Context.current()
    assert all((after_ctx[p] is None for p in properties_to_check))
