import backoff
from app.conf import Config

from httpx import (
    RemoteProtocolError,
    TimeoutException)  # => ReadTimeout, WriteTimeout, ConnectTimeout, PoolTimeout
from odes_storage.exceptions import ResponseHandlingException


_exceptions_type_to_retry = (RemoteProtocolError, TimeoutException, ResponseHandlingException)


def backoff_policy(on_backoff_handlers=None):
    """
        Returns: a retry decorator.
        Triggered in case if raised exception is: RemoteProtocolError, TimeoutException, ResponseHandlingException.

        It will retry a maximum number of `Config.de_client_backoff_max_tries.value`.
        'base', 'factor' and 'max_value' are kwargs for `backoff.expo` generator function.
    """

    return backoff.on_exception(backoff.expo,  # it will generate [1, 2, 4, 5, .. , 5]
                                _exceptions_type_to_retry,
                                max_tries=Config.de_client_backoff_max_tries.value,
                                on_backoff=on_backoff_handlers,
                                base=2,
                                factor=1,
                                max_value=Config.de_client_backoff_max_wait.value)
