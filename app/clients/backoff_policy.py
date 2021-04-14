import backoff
from app.conf import Config

from httpx import (
    RemoteProtocolError,
    TimeoutException,  # => ReadTimeout, WriteTimeout, ConnectTimeout, PoolTimeout

)


def backoff_policy(on_backoff_handlers=None):
    return backoff.on_exception(backoff.expo,
                                (RemoteProtocolError, TimeoutException),
                                max_tries=Config.de_client_backoff_max_tries.value,
                                on_backoff=on_backoff_handlers,
                                base=0.5,
                                factor=1,
                                max_value=Config.de_client_backoff_max_wait.value)
