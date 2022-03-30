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

import contextvars
from typing import Optional
import json

from app.conf import Config
from app.model.user import User
from app.injector.app_injector import AppInjector

class Context:
    """
    Immutable object to provide contextual information a long request processing
    """
    __slots__ = [
        '_tracer',
        '_logger',
        '_correlation_id',
        '_request_id',
        '_dev_mode',
        '_auth',
        '_partition_id',
        '_app_key',
        '_api_key',
        '_user',
        '_app_injector',
        '_attr_dict',
        '_x_user_id'
    ]

    def __init__(self,
                 tracer=None,
                 logger=None,
                 correlation_id: Optional[str] = None,
                 request_id: Optional[str] = None,
                 dev_mode: bool = Config.dev_mode.value,
                 auth=None,
                 partition_id: Optional[str] = None,
                 app_key: Optional[str] = None,
                 api_key: Optional[str] = None,
                 user: Optional[User] = None,
                 app_injector: Optional[AppInjector] = None,
                 x_user_id: Optional[str] = None,
                 **keys):

        self._tracer = tracer
        self._logger = logger
        self._correlation_id = correlation_id
        self._request_id = request_id
        self._dev_mode = dev_mode
        self._auth = auth
        self._partition_id = partition_id
        self._app_key = app_key
        self._api_key = api_key
        self._user = user
        self._app_injector = app_injector
        self._x_user_id = x_user_id

        # pass
        self._attr_dict = keys or {}

    __ctx_var = contextvars.ContextVar('_wdms_internal_context_var')
    """
    contextvar is natively supported in asyncio, we can take advantage of this of easily get the current context (by
    the way it may hide the potential dependency)
    """

    @classmethod
    def current(cls) -> 'Context':
        return cls.__ctx_var.get()

    @classmethod
    def clear_current(cls):
        cls.__ctx_var.set(Context())

    def set_current(self):
        Context.__ctx_var.set(self)

    @classmethod
    def set_current_with_value(cls, tracer=None, logger=None, correlation_id=None, request_id=None, auth=None,
                               partition_id=None, app_key=None, api_key=None, user=None, app_injector=None,
                               dev_mode=Config.dev_mode.value, x_user_id=None,
                               **keys) -> 'Context':
        """
        clone the current context with the given values, set the new ctx as current and returns it
        :return:
        """
        current = cls.current()
        assert current is not None, 'no existing current context'
        new_ctx = current.with_value(tracer=tracer,
                                     logger=logger,
                                     correlation_id=correlation_id,
                                     request_id=request_id,
                                     auth=auth,
                                     partition_id=partition_id,
                                     app_key=app_key,
                                     api_key=api_key,
                                     user=user,
                                     app_injector=app_injector,
                                     dev_mode=dev_mode,
                                     x_user_id=x_user_id,
                                     **keys)
        new_ctx.set_current()
        return new_ctx

    def get(self, key, default=None):
        if key in self._attr_dict:
            return self._attr_dict[key]
        if hasattr(self, '_' + key):
            return getattr(self, '_' + key)
        return default

    def __getitem__(self, key):
        if key in self._attr_dict:
            return self._attr_dict[key]

        if hasattr(self, '_' + key):
            return getattr(self, '_' + key)
        raise KeyError(key + ' is unknown')

    def __copy__(self):
        return self.__class__(
            tracer=self._tracer,
            logger=self._logger,
            correlation_id=self._correlation_id,
            request_id=self._request_id,
            dev_mode=self._dev_mode,
            auth=self._auth,
            partition_id=self._partition_id,
            app_key=self._app_key,
            api_key=self._api_key,
            user=self._user,
            app_injector=self._app_injector,
            x_user_id=self._x_user_id,
            **self._attr_dict)

    def with_correlation_id(self, correlation_id):
        clone = self.__copy__()
        clone._correlation_id = correlation_id
        return clone

    def with_request_id(self, request_id):
        clone = self.__copy__()
        clone._request_id = request_id
        return clone

    def with_auth(self, auth):
        clone = self.__copy__()
        clone._auth = auth
        return clone

    def with_partition_id(self, partition_id):
        clone = self.__copy__()
        clone._partition_id = partition_id
        return clone

    def with_x_user_id(self, x_user_id):
        clone = self.__copy__()
        clone._x_user_id = x_user_id
        return clone

    def with_user(self, user):
        clone = self.__copy__()
        clone._user = user
        return clone

    def with_app_key(self, app_key):
        clone = self.__copy__()
        clone._app_key = app_key
        return clone

    def with_api_key(self, api_key):
        clone = self.__copy__()
        clone._api_key = api_key
        return clone

    def with_injector(self, app_injector):
        clone = self.__copy__()
        clone._app_injector = app_injector
        return clone

    def with_value(self, tracer=None, logger=None, correlation_id=None, request_id=None, auth=None,
                   partition_id=None, app_key=None, api_key=None, user=None, app_injector=None,
                   dev_mode=Config.dev_mode.value, x_user_id=None, **keys) -> 'Context':
        """ Clone context, adding all keys in future logs """
        cloned = self.__class__(
            tracer=tracer or self._tracer,
            logger=logger or self._logger,
            correlation_id=correlation_id or self._correlation_id,
            request_id=request_id or self._request_id,
            dev_mode=dev_mode or self._dev_mode,
            auth=auth or self._auth,
            partition_id=partition_id or self._partition_id,
            app_key=app_key or self._app_key,
            api_key=api_key or self._api_key,
            user=user or self._user,
            app_injector=app_injector or self._app_injector,
            x_user_id=x_user_id or self._x_user_id,
            **self._attr_dict)

        if keys is not None:
            cloned._attr_dict.update(keys)
        return cloned

    @property
    def tracer(self):
        return self._tracer

    @property
    def logger(self):
        return self._logger

    @property
    def correlation_id(self) -> Optional[str]:
        return self._correlation_id

    @property
    def request_id(self) -> Optional[str]:
        return self._request_id

    @property
    def dev_mode(self) -> bool:
        return self._dev_mode

    @property
    def auth(self):
        return self._auth

    @property
    def partition_id(self) -> Optional[str]:
        return self._partition_id

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @property
    def app_key(self) -> Optional[str]:
        return self._app_key

    @property
    def user(self) -> Optional[User]:
        return self._user

    @property
    def app_injector(self) -> Optional[AppInjector]:
        return self._app_injector

    @property
    def x_user_id(self) -> Optional[str]:
        return self._x_user_id

    def __dict__(self):
        return {
            "tracer": self.tracer,
            "logger": self.logger,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "dev_mode": self.dev_mode,
            "partition_id": self.partition_id,
            "app_key": self.app_key,
            "api_key": self.api_key,
            "x_user_id": self.x_user_id,
        }

    def __repr__(self):
        return json.dumps(self.__dict__())


def get_ctx() -> Context:
    return Context.current()


def get_or_create_ctx() -> Context:
    """
    This method aims to be used in middleware, where the order of Context creation is not guaranteed
    :return an empty Context with default values
    """
    try:
        return get_ctx()
    except LookupError:
        ctx = Context()
        ctx.set_current()
    return ctx

