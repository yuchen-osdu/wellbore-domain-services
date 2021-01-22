from opencensus.trace.span import SpanKind

from app import conf
from app.utils import Context
from app.helper import traces


def _before_tracing_attributes(ctx, request):
    """
        Add request attributes + correlation id to the the current tracer's span
    """
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=traces.HTTP_HOST,
        attribute_value=request.url.host)
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=traces.HTTP_METHOD,
        attribute_value=request.method)
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=traces.HTTP_PATH,
        attribute_value=str(request.url.path))
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=traces.HTTP_URL,
        attribute_value=str(request.url))
    ctx.tracer.add_attribute_to_current_span(
        attribute_key=conf.CORRELATION_ID_HEADER_NAME,
        attribute_value=ctx.correlation_id)


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

        result = await call_next(request)
        span.add_attribute(traces.HTTP_STATUS_CODE, result.status_code)

        return result
