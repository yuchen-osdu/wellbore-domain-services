from typing import Callable

from dask.distributed import Client
from dask.utils import funcname
from dask.base import tokenize

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

    with tracer.span(name=f"Dask Worker - {funcname(target_func)}") as span:
        span.span_kind = SpanKind.CLIENT
        return target_func(*args, **kwargs)


def _create_func_key(func, *args, **kwargs):
    """
     Inspired by Dask code, it returns a hashed key based on function name and given arguments
    """
    return funcname(func) + "-" + tokenize(func, kwargs, *args)


def submit_with_trace(dask_client: Client, target_func: Callable, *args, **kwargs):
    """Submit given target_func to Distributed Dask workers and add tracing required stuff

    Note: 'dask_task_key' is manually created to easy reading of Dask's running tasks: it will display
        the effective targeted function instead of 'wrap_trace_process' used to enable tracing into Dask workers.
    """
    dask_task_key = _create_func_key(target_func, *args, **kwargs)
    kwargs['span_context'] = get_ctx().tracer.span_context
    kwargs['target_func'] = target_func
    return dask_client.submit(wrap_trace_process, *args, key=dask_task_key, **kwargs)


def map_with_trace(dask_client: Client, target_func: Callable, *args, **kwargs):
    """Submit given target_func to Distributed Dask workers and add tracing required stuff

    Note: 'dask_task_key' is manually created to easy reading of Dask's running tasks: it will display
        the effective targeted function instead of 'wrap_trace_process' used to enable tracing into Dask workers.
    """
    dask_task_key = _create_func_key(target_func, *args, **kwargs)
    kwargs['span_context'] = get_ctx().tracer.span_context
    kwargs['target_func'] = target_func
    return dask_client.map(wrap_trace_process, *args, key=dask_task_key, **kwargs)
