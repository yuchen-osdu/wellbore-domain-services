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

from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.semconv.trace import SpanAttributes

from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app import conf
from app.context import Context
from app.helper import traces_ot
from app.helper.logger import get_logger
from .backoff_policy import backoff_policy
from sys import exc_info
from traceback import format_exception


def _before_tracing_attributes(current_span, ctx, request):
    """
        Add request attributes + correlation id to the current tracer's span
    """
    current_span.set_attribute(SpanAttributes.HTTP_HOST, request.url.host)
    current_span.set_attribute(SpanAttributes.HTTP_METHOD, request.method)
    current_span.set_attribute(SpanAttributes.HTTP_ROUTE, str(request.url.path))
    current_span.set_attribute(SpanAttributes.HTTP_URL, str(request.url))
    current_span.set_attribute(conf.CORRELATION_ID_HEADER_NAME, ctx.correlation_id)


def backoff_handler_log_it(details):
    exception_type, raised_exec, tb = exc_info()
    s_stack = format_exception(exception_type, raised_exec, tb)
    get_logger().exception(f"Backoff callback, tries={details['tries']}: {raised_exec}. Stack = {s_stack}")


@backoff_policy(backoff_handler_log_it)
async def backoff_middleware(request, call_next):
    return await call_next(request)


async def client_middleware(request, call_next):
    ctx = Context.current()
    tracer = traces_ot.get_tracer()

    with tracer.start_as_current_span(name=f'[client_middleware]{request.url}', kind=SpanKind.CLIENT) as span:
        _before_tracing_attributes(span, ctx, request)

        # propagate current tracing context to outgoing request's headers
        tracing_headers = {}
        TraceContextTextMapPropagator().inject(tracing_headers)

        request.headers.update(tracing_headers)
        get_logger().debug(f"client_middleware - url: {request.url} - tracing_headers: {tracing_headers}")

        request.headers[conf.AUTHORIZATION_HEADER_NAME] = f'Bearer {ctx.auth}'
        if ctx.correlation_id:
            request.headers[conf.CORRELATION_ID_HEADER_NAME] = ctx.correlation_id
        if ctx.app_key:
            request.headers[conf.APP_KEY_HEADER_NAME] = ctx.app_key
        if ctx.x_user_id:
            request.headers[conf.X_USER_ID_HEADER_NAME] = ctx.x_user_id
        if ctx.x_collaboration:
            request.headers[conf.X_COLLABORATION_HEADER_NAME] = ctx.x_collaboration

        response = None
        try:
            response = await call_next(request)
            return response

        finally:
            status = response.status_code if response else HTTP_500_INTERNAL_SERVER_ERROR
            span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, status)
