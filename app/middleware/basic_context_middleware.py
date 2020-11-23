from fastapi import Header, Depends
from app.utils import Context, get_or_create_ctx
from app.injector.app_injector import AppInjector
from app.model.user import User
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader

from app.helper import logger
from structlog.contextvars import clear_contextvars as clear_logger_contextvars


class CreateBasicContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, injector: AppInjector, app_logger, **kwargs):
        super().__init__(**kwargs)
        self._app_injector = injector
        self._app_logger = app_logger

    async def dispatch(self, request, call_next):
        api_key = request.headers.get('x-api-key', None)
        app_key = request.headers.get('AppKey', None)
        partition_id = request.headers.get('data-partition-id', None)
        correlation_id = request.headers.get('correlation-id', request.headers.get('X-Correlation-ID', None))
        request_id = request.headers.get('X-Request-ID', None) or str(uuid.uuid4())
        anonymous_user = User(email='anonymous', authenticated=False)

        clear_logger_contextvars()
        logger.add_fields(correlation_id=correlation_id,
                          request_id=request_id,
                          partition_id=partition_id,
                          app_key=app_key,
                          api_key=api_key)

        ctx = get_or_create_ctx()
        ctx.set_current_with_value(logger=self._app_logger,
                                   correlation_id=correlation_id,
                                   request_id=request_id,
                                   partition_id=partition_id,
                                   app_key=app_key,
                                   api_key=api_key,
                                   user=anonymous_user,
                                   app_injector=self._app_injector)

        request.scope['user'] = anonymous_user

        return await call_next(request)


async def require_data_partition_id(data_partition_id: str = Header(
    'opendes',
    title='data partition id',
    description='identifier of the data partition to query',
    min_length=1)):
    Context.set_current_with_value(partition_id=data_partition_id)


appkey_header = APIKeyHeader(name='appkey')


async def require_appkey(appkey: APIKeyHeader = Depends(appkey_header)):
    Context.set_current_with_value(app_key=appkey)
