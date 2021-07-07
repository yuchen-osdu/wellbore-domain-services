from opencensus.trace.span import SpanKind
from opencensus.trace import tracer as open_tracer
from opencensus.trace.samplers import AlwaysOnSampler

from app.helper.traces import create_exporter
from app.conf import Config


def wrap_trace_process(target_func, span_context, *args, **kwargs):
    if not span_context:
        raise AttributeError("span_content cannot be null")

    tracer = open_tracer.Tracer(span_context=span_context,
                                sampler=AlwaysOnSampler(),
                                exporter=create_exporter(service_name=Config.service_name.value))

    with tracer.span(name=f"Dask Worker - {target_func.__name__}") as span:
        span.span_kind = SpanKind.CLIENT
        return target_func(*args, **kwargs)
