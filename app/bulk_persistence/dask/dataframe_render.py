import ast
from typing import List, Set, Optional, Iterable

import pandas as pd
import dask.dataframe as dd
from natsort import natsorted
from fastapi import Response

from .traces import trace_dataframe_attributes
from .errors import internal_bulk_exceptions, FilterError, BulkCurvesNotFound
from .dask_bulk_storage import DaskBulkStorage
from ..capture_timings import capture_timings
from ..bulk_filter import BulkReadFilterOperator, BulkReadFilters
from ..model_chunking import GetDataParams, DataframeDescribe
from ..mime_types import MimeType, MimeTypes
from ..json_orient import JSONOrient
from ..dataframe_serializer import DataframeSerializerAsync
from ..dataframe_columns import select_columns

from app.helper.traces_ot import get_tracer
_tracer = get_tracer()


class DataFrameRender:
    @staticmethod
    async def _compute(df, dask_blob_storage):
        if isinstance(df, pd.DataFrame):
            return df
        return await dask_blob_storage.client.compute(df)

    @staticmethod
    async def _get_size(df, dask_blob_storage):
        if isinstance(df, pd.DataFrame):
            return len(df.index)
        return await dask_blob_storage._submit_with_trace(len, df.index)

    @staticmethod
    def _select_range_impl(df: dd.DataFrame, limit, offset, index):
        if df.known_divisions and index is not None:
            if offset:
                index = index[offset:]
            if limit:
                index = index[:limit]
            return df.loc[list(index)]  # this works only if divisions are known

        dataframe_list = []
        CONCURRENT_READ = 1
        for nth in range(0, df.npartitions, CONCURRENT_READ):
            dataframe = df.partitions[nth:nth+CONCURRENT_READ].compute()
            partition_len = len(dataframe.index)

            if offset and partition_len < offset:
                offset -= partition_len
                continue  # skip the partition
            if offset:
                dataframe = dataframe.iloc[offset:]
                offset = 0
            if limit:
                dataframe = dataframe.iloc[:limit]
                limit -= len(dataframe.index)

            dataframe_list.append(dataframe)
            if limit is not None and limit <= 0:
                break  # stop when we have the requested data
        if not dataframe_list:
            return df.head(0)  # return an empty dataframe
        return pd.concat(dataframe_list)

    @staticmethod
    @_tracer.start_as_current_span('select_range')
    @capture_timings('select_range')
    async def select_range(df: dd.DataFrame, offset, limit, dask_blob_storage: DaskBulkStorage, index=None):
        if offset or limit:
            return await dask_blob_storage._submit_with_trace(DataFrameRender._select_range_impl,
                                                              df, limit, offset, index)
        return df

    @staticmethod
    @_tracer.start_as_current_span('get_matching_column')
    def get_matching_columns(selection: List[str], cols: Set[str]) -> List[str]:
        matching_columns, curves_non_existent = select_columns(selection, cols)
        if curves_non_existent:
            raise BulkCurvesNotFound(curves=curves_non_existent)

        return matching_columns

    @staticmethod
    @_tracer.start_as_current_span('apply_filter')
    def apply_filter(dataframe, filters: BulkReadFilters):
        """
        apply the given bulk filter on the dataframe
        :param dataframe: dataframe on which apply the filters
        :param filters: the filters
        return filtered dataframe
        """

        operator_to_function = {
            BulkReadFilterOperator.Equal:
                lambda df, col, val: df[col] == val,

            BulkReadFilterOperator.NotEqual:
                lambda df, col, val: df[col] != val,

            BulkReadFilterOperator.LessOrEqual:
                lambda df, col, val: df[col] <= val,

            BulkReadFilterOperator.Less:
                lambda df, col, val: df[col] < val,

            BulkReadFilterOperator.Greater:
                lambda df, col, val: df[col] > val,

            BulkReadFilterOperator.GreaterOrEqual:
                lambda df, col, val: df[col] >= val,

            BulkReadFilterOperator.In:
                lambda df, col, val: df[col].isin(val)
        }

        for col_name, operator, value in filters.all_filters():
            try:
                new_value = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                new_value = value

            if dataframe[col_name].dtype == object:
                if isinstance(new_value, tuple):
                    new_value = [str(v) for v in new_value]
                else:
                    new_value = str(new_value)

            filter_function = operator_to_function[operator]
            try:
                dataframe = dataframe[filter_function(dataframe, col_name, new_value)]
            except ValueError:
                raise FilterError('the value is not valid for this operation')
            except TypeError:
                raise FilterError('Incompatible types in filtering')

        return dataframe


    @staticmethod
    @internal_bulk_exceptions
    @_tracer.start_as_current_span('process_params')
    async def process_params(df,
                             params: GetDataParams,
                             filters: BulkReadFilters,
                             dask_blob_storage: DaskBulkStorage,
                             f_index):
        """
        pass filters as a parameter here to avoid using params.get_filter() to parse filters 2 times
        """
        if isinstance(df, pd.DataFrame):
            df = dd.from_pandas(df, npartitions=1)

        if filters.has_filter():
            df = DataFrameRender.apply_filter(df, filters)

        if params.curves:
            selection = params.get_curves_list()
            columns = DataFrameRender.get_matching_columns(selection, set(df.columns))
            df = df[columns]  # columns are ordered as the user requested
        else:
            df = df[natsorted(df.columns)]  # columns are ordered by natural sort

        if filters.has_filter() and (params.offset or params.limit):
            f_index = dask_blob_storage.client.compute(df.index)

        df = await DataFrameRender.select_range(df, params.offset, params.limit, dask_blob_storage, f_index)

        return df

    @staticmethod
    @internal_bulk_exceptions
    @_tracer.start_as_current_span('df_render')
    async def df_render(df, dask_blob_storage, params: GetDataParams,
                        render_type: Optional[MimeType] = None,
                        orient: Optional[JSONOrient] = None,
                        columns: Optional[Iterable[str]] = None):
        if params.describe:
            nb_rows = await DataFrameRender._get_size(df, dask_blob_storage)
            if params.curves is None and columns:
                columns = natsorted(list(columns))
            else:
                columns = list(df.columns)

            return DataframeDescribe(
                numberOfRows=nb_rows,
                columns=columns
            )

        pdf = await DataFrameRender._compute(df, dask_blob_storage)
        pdf.index.name = None  # TODO
        trace_dataframe_attributes(pdf)

        if render_type == MimeTypes.PARQUET:
            content = await DataframeSerializerAsync().to_parquet(pdf)
            return Response(content, media_type=render_type.type)

        if render_type == MimeTypes.JSON:
            content = await DataframeSerializerAsync().to_json(pdf, index=True, date_format='iso', orient=orient.value)
            return Response(content, media_type=render_type.type)

        raise ValueError("Invalid render type")
