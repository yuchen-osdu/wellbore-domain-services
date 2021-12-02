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

import uuid

from fastapi import Depends, Header
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import clear_contextvars as clear_logger_contextvars

import app.helper.utils as logger_utils
from app import conf
from app.injector.app_injector import AppInjector
from app.model.user import User
from app.utils import Context, get_or_create_ctx
from app.helper.logger import get_logger


class CreateBasicContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, injector: AppInjector, **kwargs):
        super().__init__(**kwargs)
        self._app_injector = injector

    @staticmethod
    def _add_csp_header(request, response):
        """
        Returns the response with the additional CSP headers added to allow for swagger js and css files from the given domains.
        """
        if "/docs" in request.url.path:
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' *.jsdelivr.net 'unsafe-inline'; style-src 'self' *.jsdelivr.net; img-src 'self' *.tiangolo.com data:;"

    async def dispatch(self, request, call_next):
        api_key = request.headers.get('x-api-key', None)
        app_key = request.headers.get(conf.APP_KEY_HEADER_NAME, None)
        partition_id = request.headers.get('data-partition-id', None)
        x_user_id = request.headers.get(conf.X_USER_ID_HEADER_NAME, None)
        correlation_id = request.headers.get(conf.CORRELATION_ID_HEADER_NAME, str(uuid.uuid4()))
        request_id = request.headers.get(conf.REQUEST_ID_HEADER_NAME, str(uuid.uuid4()))
        anonymous_user = User(email='anonymous', authenticated=False)

        clear_logger_contextvars()
        logger_utils.add_fields(correlation_id=correlation_id,
                                request_id=request_id,
                                partition_id=partition_id,
                                app_key=app_key,
                                api_key=api_key)

        ctx = get_or_create_ctx()
        ctx.set_current_with_value(logger=get_logger(),
                                   correlation_id=correlation_id,
                                   request_id=request_id,
                                   partition_id=partition_id,
                                   app_key=app_key,
                                   api_key=api_key,
                                   user=anonymous_user,
                                   x_user_id=x_user_id,
                                   app_injector=self._app_injector)

        request.scope['user'] = anonymous_user

        response = await call_next(request)
        self._add_csp_header(request, response)
        return response


async def require_data_partition_id(
        data_partition_id: str = Header(default=None,
                                        title='data partition id',
                                        description='identifier of the data partition to query',
                                        min_length=1)):
    Context.set_current_with_value(partition_id=data_partition_id)


appkey_header = APIKeyHeader(name=conf.APP_KEY_HEADER_NAME)


async def require_appkey(appkey: APIKeyHeader = Depends(appkey_header)):
    Context.set_current_with_value(app_key=appkey)
