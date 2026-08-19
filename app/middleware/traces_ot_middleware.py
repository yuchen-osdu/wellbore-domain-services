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

from typing import Any, List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace import Status, StatusCode, SpanKind


from app.helper import utils
from app.context import get_or_create_ctx
from app import conf
from app.helper.logger import get_logger
from app.helper import traces_ot


class TracingMiddlewareOT(BaseHTTPMiddleware):
    def __init__(self, app, *, skip_for_path_suffix: List[str], **kwargs):
        super().__init__(app, **kwargs)
        self._skip_for_path_suffix = skip_for_path_suffix

    @staticmethod
    def _before_request(request: Request):
        current_span = trace.get_current_span()

        current_span.set_attribute(SpanAttributes.HTTP_HOST, request.url.hostname)
        current_span.set_attribute(SpanAttributes.HTTP_METHOD, request.method)
        current_span.set_attribute(SpanAttributes.HTTP_ROUTE, utils.truncate_long_url(request.url.path))
        current_span.set_attribute(SpanAttributes.HTTP_URL, utils.truncate_long_url(str(request.url)))

        ctx_correlation_id = get_or_create_ctx().correlation_id
        correlation_id = ctx_correlation_id if ctx_correlation_id is not None \
            else request.headers.get(conf.CORRELATION_ID_HEADER_NAME)
        if correlation_id:
            current_span.set_attribute(conf.CORRELATION_ID_HEADER_NAME, correlation_id)
    
        ctx_partition_id = get_or_create_ctx().partition_id
        partition_id = ctx_partition_id if ctx_partition_id is not None \
            else request.headers.get(conf.PARTITION_ID_HEADER_NAME)
        if partition_id:
            current_span.set_attribute(conf.PARTITION_ID_HEADER_NAME, partition_id)

        ctx_x_user_id = get_or_create_ctx().x_user_id
        x_user_id = ctx_x_user_id if ctx_x_user_id is not None \
            else request.headers.get(conf.X_USER_ID_HEADER_NAME)
        if x_user_id:
            current_span.set_attribute('user-id', x_user_id)

        if request_content_type := request.headers.get("Content-type"):
            current_span.set_attribute("request.header Content-type", request_content_type)

        if request_content_length := request.headers.get("Content-Length"):
            current_span.set_attribute("request.header Content-length", request_content_length)

        if app_id := request.headers.get(conf.APP_ID_HEADER_NAME):
            current_span.set_attribute(conf.APP_ID_HEADER_NAME, app_id)

    @staticmethod
    def _after_request(request: Request, response: Response):

        current_span = trace.get_current_span()

        status = response.status_code if response else HTTP_500_INTERNAL_SERVER_ERROR
        current_span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, status)

        http_route = request.scope['route'].path if "route" in request.scope else request.scope['path']
        current_span.set_attribute(SpanAttributes.HTTP_ROUTE, utils.truncate_long_url(http_route))

        if response:
            response_content_type = response.headers.get("Content-type")
            current_span.set_attribute("response.header Content-type", response_content_type)

            response_content_length = response.headers.get("Content-Length")
            current_span.set_attribute("response.header Content-length", response_content_length)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path.endswith(tuple(self._skip_for_path_suffix)):
            # early call_next and return if we want to skip the middleware behaviour
            return await call_next(request)

        tracer = traces_ot.get_tracer()
        tracing_ctx = TraceContextTextMapPropagator().extract(carrier=request.headers)

        with tracer.start_as_current_span(name=request.url.path, kind=SpanKind.SERVER, context=tracing_ctx) as span:
            self._before_request(request)
            get_logger().debug(f'Request start: {request.method} {request.url}')

            response = None
            try:
                response = await call_next(request)
                return response
            except Exception:
                # parent_span.record_exception(ex)
                span.set_status(Status(StatusCode.ERROR))
                get_logger().exception(f"Exception occurred when calling: {request.url.path}")
                raise
            finally:
                status = response.status_code if response else HTTP_500_INTERNAL_SERVER_ERROR
                get_logger().info(utils.process_message(request, status))
                self._after_request(request, response)
