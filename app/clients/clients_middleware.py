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

from opencensus.trace.span import SpanKind
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app import conf
from app.utils import Context
from app.helper import utils, traces
from .backoff_policy import backoff_policy
from sys import exc_info
from traceback import format_exception


def _before_tracing_attributes(ctx, request):
    """
        Add request attributes + correlation id to the the current tracer's span
    """
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=utils.HTTP_HOST,
        attribute_value=request.url.host)
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=utils.HTTP_METHOD,
        attribute_value=request.method)
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=utils.HTTP_PATH,
        attribute_value=str(request.url.path))
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=utils.HTTP_URL,
        attribute_value=str(request.url))
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=conf.CORRELATION_ID_HEADER_NAME,
        attribute_value=ctx.correlation_id)


def backoff_handler_log_it(details):
    ctx = Context.current()

    exception_type, raised_exec, tb = exc_info()
    s_stack = format_exception(exception_type, raised_exec, tb)
    ctx.logger.exception(f"Backoff callback, tries={details['tries']}: {raised_exec}. Stack = {s_stack}")


@backoff_policy(backoff_handler_log_it)
async def backoff_middleware(request, call_next):
    return await call_next(request)


async def client_middleware(request, call_next):
    ctx = Context.current()

    with ctx.tracer.span(name=f'[client_middleware]{request.url}') as span:
        span.span_kind = SpanKind.CLIENT
        _before_tracing_attributes(ctx, request)

        # propagate current tracing context to outgoing request's headers
        tracing_headers = traces.get_trace_propagator().to_headers(span.context_tracer.span_context)

        request.headers.update(tracing_headers)
        ctx.logger.debug(f"client_middleware - url: {request.url} - tracing_headers: {tracing_headers}")

        request.headers[conf.AUTHORIZATION_HEADER_NAME] = f'Bearer {ctx.auth}'
        if ctx.correlation_id:
            request.headers[conf.CORRELATION_ID_HEADER_NAME] = ctx.correlation_id
        if ctx.app_key:
            request.headers[conf.APP_KEY_HEADER_NAME] = ctx.app_key
        if ctx.x_user_id:
            request.headers[conf.X_USER_ID_HEADER_NAME] = ctx.x_user_id

        response = None
        try:
            response = await call_next(request)
            return response

        finally:
            status = response.status_code if response else HTTP_500_INTERNAL_SERVER_ERROR
            span.add_attribute(utils.HTTP_STATUS_CODE, status)
