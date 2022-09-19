from typing import Callable, Union
from enum import Enum

from dask.distributed import Client
import pandas as pd
from dask.utils import funcname
from dask.base import tokenize

from opencensus.trace.span import SpanKind
from opencensus.trace import tracer as open_tracer
from opencensus.trace.samplers import AlwaysOnSampler

from app.conf import Config
from app.helper import traces
from app.context import get_ctx
from opencensus.trace import execution_context
from . import dask_worker_write_bulk as bulk_writer

_EXPORTER = None


def wrap_trace_process(*args, **kwargs):
    global _EXPORTER

    tracing_headers = kwargs.pop('tracing_headers')
    target_func = kwargs.pop('target_func')
    if not tracing_headers or not target_func:
        raise AttributeError("Keyword arguments should contain 'target_func' and 'tracing_headers'")

    if _EXPORTER is None:
        _EXPORTER = traces.create_exporter(service_name=Config.service_name.value, config=Config)

    span_context = traces.get_trace_propagator().from_headers(tracing_headers)
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
    tracing_headers = traces.get_trace_propagator().to_headers(get_ctx().tracer.span_context)
    kwargs['tracing_headers'] = tracing_headers
    kwargs['target_func'] = target_func

    dask_task_key = _create_func_key(target_func, *args, **kwargs)

    return dask_client.submit(wrap_trace_process, *args, key=dask_task_key, **kwargs)


def map_with_trace(dask_client: Client, target_func: Callable, *args, **kwargs):
    """Submit given target_func to Distributed Dask workers and add tracing required stuff

    Note: 'dask_task_key' is manually created to easy reading of Dask's running tasks: it will display
        the effective targeted function instead of 'wrap_trace_process' used to enable tracing into Dask workers.
    """
    tracing_headers = traces.get_trace_propagator().to_headers(get_ctx().tracer.span_context)
    kwargs['tracing_headers'] = tracing_headers
    kwargs['target_func'] = target_func

    dask_task_key = _create_func_key(target_func, *args, **kwargs)

    return dask_client.map(wrap_trace_process, *args, key=dask_task_key, **kwargs)


class TracingMode(Enum):
    """ Allow to determine which mode of adding attributes on tracing span is needed. """
    CURRENT_SPAN = 1
    ROOT_SPAN = 2


def _add_trace_attributes(attributes: dict, tracing_mode: TracingMode):
    """
        If tracer exists, add custom key:value as attributes on root or current span according value of 'tracing_mode'.
        NOTE: if called by a Dask worker, the parent span is the one created by `wrap_trace_process` function above.
    """
    opencensus_tracer = execution_context.get_opencensus_tracer()
    if opencensus_tracer is None or not hasattr(opencensus_tracer, 'tracer'):
        return

    span = None

    if tracing_mode == TracingMode.CURRENT_SPAN:
        span = opencensus_tracer.current_span()
    elif tracing_mode == TracingMode.ROOT_SPAN:
        existing_spans = opencensus_tracer.tracer.list_collected_spans()
        span = existing_spans[0] if existing_spans else None

    if not span:
        return

    for k, v in attributes.items():
        span.add_attribute(attribute_key=k,
                           attribute_value=v)


def trace_attributes_root_span(attributes):
    """ Add attributes to root tracing span """
    _add_trace_attributes(attributes, TracingMode.ROOT_SPAN)


def trace_attributes_current_span(attributes):
    """ Add attributes to current tracing span """
    _add_trace_attributes(attributes, TracingMode.CURRENT_SPAN)


def trace_dataframe_attributes(df: Union[pd.DataFrame, bulk_writer.DataframeBasicDescribe]):
    """
        Add dataframe shape into current tracing span if tracer exists
    """
    if type(df) is pd.DataFrame:
        df = bulk_writer.basic_describe(df)

    trace_attributes_current_span({
        "df rows count": df.row_count,
        "df columns count": df.column_count,
        "df index start": df.index_start,
        "df index end": df.index_end,
        "df index type": df.index_type,
    })
