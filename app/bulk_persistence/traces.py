from typing import Union
from enum import Enum

import pandas as pd

from app.helper import traces_ot

from .consistency_checks import BulkInfoForConsistency
from .model_chunking import DataframeBasicDescribe

_EXPORTER = None


class TracingMode(Enum):
    """ Allow to determine which mode of adding attributes on tracing span is needed. """
    CURRENT_SPAN = 1
    ROOT_SPAN = 2


def _add_trace_attributes(attributes: dict, tracing_mode: TracingMode):
    """
        If tracer exists, add custom key:value as attributes on root or current span according value of 'tracing_mode'.
        NOTE: if called by a Dask worker, the parent span is the one created by `wrap_trace_process` function above.
    """
    from opentelemetry import trace
    _tracer = traces_ot.get_tracer()

    if _tracer is None:
        return

    span = None

    if tracing_mode == TracingMode.CURRENT_SPAN:
        span = trace.get_current_span()
    elif tracing_mode == TracingMode.ROOT_SPAN:
        pass
        # existing_spans = opencensus_tracer.tracer.list_collected_spans()
        # span = existing_spans[0] if existing_spans else None

    if not span:
        return

    for k, v in attributes.items():
        span.set_attribute(key=k, value=v)


def trace_attributes_root_span(attributes):
    """ Add attributes to root tracing span """
    _add_trace_attributes(attributes, TracingMode.ROOT_SPAN)


def trace_attributes_current_span(attributes):
    """ Add attributes to current tracing span """
    _add_trace_attributes(attributes, TracingMode.CURRENT_SPAN)


def trace_dataframe_attributes(df: Union[pd.DataFrame, BulkInfoForConsistency]):
    """
        Add dataframe shape into current tracing span if tracer exists
    """
    if type(df) is pd.DataFrame:
        df = basic_describe(df)

    trace_attributes_current_span({
        "df rows count": df.row_count,
        "df columns count": df.column_count,
        "df index start": df.index_start,
        "df index end": df.index_end,
        "df index type": df.index_type,
    })


def basic_describe(df: pd.DataFrame) -> DataframeBasicDescribe:
    full_cols = df.columns.tolist()
    if len(full_cols) > 20:  # truncate if too many columns, show 10 first and 10 last
        cols = [*full_cols[0:10], '...', *full_cols[-10:]]
    else:
        cols = full_cols

    index_exists = len(df.index)
    return DataframeBasicDescribe(rowCount=len(df.index),
                                  columnCount=len(full_cols),
                                  columns=cols,
                                  indexStart=str(df.index[0]) if index_exists else "0",
                                  indexEnd=str(df.index[-1]) if index_exists else "0",
                                  indexType=str(df.index.dtype) if index_exists else "")
