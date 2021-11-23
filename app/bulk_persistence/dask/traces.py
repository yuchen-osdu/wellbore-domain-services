from typing import Callable

from dask.distributed import Client

from opencensus.trace.span import SpanKind
from opencensus.trace import tracer as open_tracer
from opencensus.trace.samplers import AlwaysOnSampler

from app.conf import Config
from app.helper.traces import create_exporter
from app.utils import get_ctx

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

    with tracer.span(name=f"Dask Worker - {target_func.__name__}") as span:
        span.span_kind = SpanKind.CLIENT
        return target_func(*args, **kwargs)


def submit_with_trace(dask_client: Client, target_func: Callable, *args, **kwargs):
    """Submit given target_func to Distributed Dask workers and add tracing required stuff"""
    kwargs['span_context'] = get_ctx().tracer.span_context
    kwargs['target_func'] = target_func
    return dask_client.submit(wrap_trace_process, *args, **kwargs)


def map_with_trace(dask_client: Client, target_func: Callable, *args, **kwargs):
    """Submit given target_func to Distributed Dask workers and add tracing required stuff"""
    kwargs['span_context'] = get_ctx().tracer.span_context
    kwargs['target_func'] = target_func
    return dask_client.map(wrap_trace_process, *args, **kwargs)
