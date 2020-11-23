from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.helper import traces
from opencensus.trace import tracer as open_tracer
from opencensus.trace.samplers import ProbabilitySampler
from app.utils import get_or_create_ctx
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator


class TracingMiddleware(BaseHTTPMiddleware):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use default Context propagator for now. Todo: add mechanism to initialize propagator from env variable.
        self._trace_propagator = TraceContextPropagator()

    @staticmethod
    def _before_request(request: Request, tracer: open_tracer.Tracer):
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_HOST,
            attribute_value=request.url.hostname)
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_METHOD,
            attribute_value=request.method)
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_PATH,
            attribute_value=str(request.url.path))
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_URL,
            attribute_value=str(request.url))

    @staticmethod
    def _after_request(response: Response, tracer):
        tracer.add_attribute_to_current_span(
            attribute_key=traces.HTTP_STATUS_CODE,
            attribute_value=response.status_code)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """
        Create a new span for each request, add attributes to this span and add status code after handling request
        """
        trace_exporter = request.app.trace_exporter
        span_context = self._trace_propagator.from_headers(request.headers)

        # Reload the tracer with the new span context
        tracer = open_tracer.Tracer(span_context=span_context, sampler=ProbabilitySampler(0.1),
                                    propagator=self._trace_propagator, exporter=trace_exporter)

        correlation_id = request.headers.get('correlation-id', request.headers.get('X-Correlation-ID', None))

        ctx = get_or_create_ctx()
        ctx.set_current_with_value(tracer=tracer)

        with tracer.span(name=request.url.path):
            tracer.add_attribute_to_current_span(attribute_key='X-Correlation-ID', attribute_value=correlation_id)
            self._before_request(request, tracer)
            response = await call_next(request)
            self._after_request(response, tracer)

        return response
