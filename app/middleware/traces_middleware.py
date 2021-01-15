from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.helper import traces
from opencensus.trace import tracer as open_tracer
from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.trace.span import SpanKind
from app.utils import get_or_create_ctx
from app import conf
from inspect import isfunction as is_function


class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._trace_propagator = traces.get_trace_propagator()

    @staticmethod
    def _retrieve_raw_path(request):
        """
        Returns the raw path of given request, else default request's url path
        E.g.:
            /ddms/v2/wellbores/{wellboreid} instead of /ddms/v2/wellbores/opendes:doc:blablabla14587

        It retrieves the raw path by finding the APIRoute object by name. By default the name of the route is the name
         of python method where there is the implementation.


        >>> @router.get('/wellbores/{wellboreid}')
        >>> async def get_wellbore(wellboreid: str, ctx: Context):
        >>>     # instructions here
        In this example 'get_wellbore' is called_endpoint_func variable, this function's name is needed to retrieve
        the APIRoute that contains the raw path.
        """
        called_endpoint_func = request.scope['endpoint']

        if called_endpoint_func and is_function(called_endpoint_func):
            function_name = called_endpoint_func.__name__
            called_routes = [route for route in request.app.routes
                             if route.name == function_name]
            if called_routes:
                return called_routes[0].path

        return request.url.path

    @staticmethod
    def _before_request(request: Request, tracer: open_tracer.Tracer):
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_HOST,
            attribute_value=request.url.hostname)
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_METHOD,
            attribute_value=request.method)

        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_ROUTE,
            attribute_value=request.url.path)
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_PATH,
            attribute_value=str(request.url.path))
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_URL,
            attribute_value=str(request.url))

        ctx_correlation_id = get_or_create_ctx().correlation_id
        correlation_id = ctx_correlation_id if ctx_correlation_id is not None \
            else request.headers.get(conf.CORRELATION_ID_HEADER_NAME)
        tracer.add_attribute_to_current_span(
            attribute_key=conf.CORRELATION_ID_HEADER_NAME,
            attribute_value=correlation_id)

    @staticmethod
    def _after_successful_request(response: Response, tracer):
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_STATUS_CODE,
            attribute_value=response.status_code)

    @staticmethod
    def _after_request(request, tracer):
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_ROUTE,
            attribute_value=TracingMiddleware._retrieve_raw_path(request))

    async def dispatch(self, request: Request, call_next: Any) -> Response:

        # Create tracing context, from headers if exists, else create a new one
        span_context = self._trace_propagator.from_headers(request.headers)

        tracer = open_tracer.Tracer(span_context=span_context,
                                    sampler=AlwaysOnSampler(),
                                    propagator=self._trace_propagator,
                                    exporter=request.app.trace_exporter)

        ctx = get_or_create_ctx()
        with tracer.span(request.url.path) as parent_span:
            parent_span.span_kind = SpanKind.SERVER
            ctx.set_current_with_value(tracer=tracer)

            self._before_request(request, tracer)
            ctx.logger.debug(f'Request start: {request.method} {request.url}')

            response = None
            try:
                response = await call_next(request)
                self._after_successful_request(response, tracer)
                return response

            finally:
                status = response.status_code if response else HTTP_500_INTERNAL_SERVER_ERROR
                ctx.logger.info(traces.process_message(request, status))
                self._after_request(request, tracer)
