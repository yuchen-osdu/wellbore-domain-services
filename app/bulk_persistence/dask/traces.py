from dask.utils import funcname
from dask.base import tokenize

from opencensus.trace.span import SpanKind
from opencensus.trace import tracer as open_tracer
from opencensus.trace.samplers import AlwaysOnSampler

from app.helper.traces import create_exporter
from app.conf import Config

_EXPORTER = None


def wrap_trace_process(*args, **kwargs):
    global _EXPORTER

    target_func = kwargs.pop('target_func')
    span_context = kwargs.pop('span_context')
    if not span_context or not target_func:
        raise AttributeError("Keyword arguments should contain 'target_func' and 'span_context'")

    if _EXPORTER is None:
        _EXPORTER = create_exporter(service_name=Config.service_name.value)

    tracer = open_tracer.Tracer(span_context=span_context,
                                sampler=AlwaysOnSampler(),
                                exporter=_EXPORTER)

    with tracer.span(name=f"Dask Worker - {funcname(target_func)}") as span:
        span.span_kind = SpanKind.CLIENT
        return target_func(*args, **kwargs)


def _create_func_key(func, *args, **kwargs):
    """
     Inspired by Dask code, it returns a hashed key based on function name and given arguments
    """
    return funcname(func) + "-" + tokenize(func, kwargs, *args)
