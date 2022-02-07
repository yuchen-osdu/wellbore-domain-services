from fastapi import HTTPException, Request, status
from fastapi.routing import APIRoute

from typing import List, Set, Optional
import re
from contextlib import suppress
from fastapi.responses import Response
import dask.dataframe as dd
import pandas as pd
from natsort import natsorted
import ast

from app.bulk_persistence.dask.errors import FilterError, internal_bulk_exceptions, BulkCurvesNotFound
from app.bulk_persistence.dask.traces import trace_dataframe_attributes
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dataframe_validators import auto_cast_columns_to_string, columns_type_must_be_string, \
    no_validation, DataFrameValidationFunc
from app.bulk_persistence import DataframeSerializerAsync
from app.bulk_persistence.mime_types import MimeTypes
from app.bulk_persistence import JSONOrient

from app.clients.storage_service_client import get_storage_record_service
from app.utils import capture_timings, get_ctx, OpenApiHandler, Context
from app.helper.traces import with_trace
from app.model.filter import BulkReadFilterOperator, BulkReadFilters
from app.model.model_chunking import GetDataParams, DataframeDescribe
from app.routers.bulk.bulk_uri_dependencies import BulkIdAccess
from pyarrow.lib import ArrowInvalid


def update_operation_ids(wdms_app):
    """ Ensure all operation_id are uniques """

    operation_ids = set()
    for route in wdms_app.routes:
        if isinstance(route, APIRoute):
            if route.operation_id in operation_ids:
                # duplicate detected
                new_operation_id = route.unique_id
                if route.operation_id in OpenApiHandler._handlers:
                    OpenApiHandler._handlers[new_operation_id] = OpenApiHandler._handlers[route.operation_id]
                route.operation_id = new_operation_id
            else:
                operation_ids.add(route.operation_id)


async def set_v3_input_dataframe_check(request: Request):
    """
     Inject into request state (c.f. https://www.starlette.io/requests/#other-state)
     the check function. It aims for v3 bulk APIs
    """
    request.state.check_input_df_func = columns_type_must_be_string


async def set_legacy_input_dataframe_check(request: Request):
    """
    Inject into request state (c.f. https://www.starlette.io/requests/#other-state) the check function.
    For legacy routes, the check function is set according to content-type:
        - parquet: no backward compatibility required, same function that v3 bulk
        - json: backward compatibility required, the check function will cast column name type as string
     """
    content_type = request.headers.get('Content-Type')
    if MimeTypes.PARQUET.match(content_type):
        request.state.check_input_df_func = columns_type_must_be_string
    else:
        request.state.check_input_df_func = auto_cast_columns_to_string


def get_df_validation_func(request: Request) -> DataFrameValidationFunc:
    """
    Retrieve from request state (c.f. https://www.starlette.io/requests/#other-state) the injected input check function.
    This function is injected when mounting the bulk router into the fastApi app as router's 'dependencies'
    in module app/wdms_app.

    NOTE: attribute name 'check_input_df_func' which contains the function should be IDENTICAL
    that defined in above functions

    return: guarantee to return a not None dataframe validation function
    """
    if not request.state.check_input_df_func:
        return no_validation
    return request.state.check_input_df_func


@with_trace("get_df_from_request")
async def get_df_from_request(request: Request) -> pd.DataFrame:
    """ Extract dataframe from request """

    ct = request.headers.get('Content-Type', '')
    if MimeTypes.PARQUET.match(ct):
        content = await request.body()  # request.stream()
        try:
            return await DataframeSerializerAsync().read_parquet(content)
        except (OSError, ArrowInvalid) as err:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f'{err}')  # TODO

    if MimeTypes.JSON.match(ct):
        content = await request.body()  # request.stream()
        try:
            return await DataframeSerializerAsync().read_json(content, JSONOrient.split)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail='invalid body')  # TODO

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f'Invalid content-type, "{ct}" is not supported')


@with_trace("with_dask_blob_storage")
async def with_dask_blob_storage() -> DaskBulkStorage:
    return await get_ctx().app_injector.get(DaskBulkStorage)


class DataFrameRender:
    @staticmethod
    async def compute(df):
        if isinstance(df, pd.DataFrame):
            return df
        driver = await with_dask_blob_storage()
        return await driver.client.compute(df)

    @staticmethod
    async def load_index(record_id: str, bulk_id: str, dask_blob_storage: DaskBulkStorage):
        return await dask_blob_storage._future_load_index(record_id, bulk_id)

    @staticmethod
    async def get_size(df):
        if isinstance(df, pd.DataFrame):
            return len(df.index)
        driver = await with_dask_blob_storage()
        return await driver._submit_with_trace(lambda: len(df.index))

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
    @with_trace('select_range')
    @capture_timings('select_range')
    async def select_range(df: dd.DataFrame, offset, limit, dask_blob_storage: DaskBulkStorage, index=None):
        if offset or limit:
            return await dask_blob_storage._submit_with_trace(DataFrameRender._select_range_impl,
                                                              df, limit, offset, index)
        return df

    re_array_selection = re.compile(r'^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$')

    @staticmethod
    def _get_matching_columns_from_selection(selection: str, all_columns=Set[str]) -> List[str]:
        m_sel = DataFrameRender.re_array_selection.match(selection)
        if m_sel and m_sel['stop']:  # selection like col_name[<start>:<stop>]
            col_name = m_sel['name']
            with suppress(ValueError):  # suppress int conversion exceptions
                requested_columns = (f'{col_name}[{i}]' for i in range(int(m_sel['start']), int(m_sel['stop'])+1))  # TODO we may want to support floating point values ?
                return all_columns.intersection(requested_columns)

        def is_matching(col: str):
            if not col.startswith(selection):
                return False
            if len(col) == len(selection):  # exact match
                return True
            m_col = DataFrameRender.re_array_selection.match(col)
            if m_col:  # if selection is 'col_name', col_name[*] should match
                return m_col['name'] == selection
            return False

        return [c for c in all_columns if is_matching(c)]

    @staticmethod
    @with_trace('get_matching_column')
    def get_matching_columns(selection: List[str], cols: Set[str]) -> List[str]:
        selected = {}
        curves_non_existent = []

        for sel in selection:
            matching_columns = DataFrameRender._get_matching_columns_from_selection(sel, cols)
            if matching_columns:
                selected.update({column: 1 for column in natsorted(matching_columns)})
            else:
                curves_non_existent.append(sel)

        if curves_non_existent:
            raise BulkCurvesNotFound(curves=curves_non_existent)

        return list(selected.keys())

    @staticmethod
    @with_trace('apply_filter')
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
                dataframe = dataframe.loc[filter_function(dataframe, col_name, new_value)]
            except ValueError:
                raise FilterError('the value is not valid for this operation')
        return dataframe

    @staticmethod
    @internal_bulk_exceptions
    @with_trace('process_params')
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
    @with_trace('df_render')
    async def df_render(df, params: GetDataParams, accept: str = None, orient: Optional[JSONOrient] = None, stat=None):
        if params.describe:
            nb_rows = await DataFrameRender.get_size(df)
            if params.curves is None and stat:
                columns = natsorted(list(stat['schema']))
            else:
                columns = list(df.columns)

            return DataframeDescribe(
                numberOfRows=nb_rows,
                columns=columns
            )

        pdf = await DataFrameRender.compute(df)
        pdf.index.name = None  # TODO
        trace_dataframe_attributes(pdf)

        if not accept or MimeTypes.PARQUET.type in accept:
            content = await DataframeSerializerAsync().to_parquet(pdf)
            return Response(content, media_type=MimeTypes.PARQUET.type)

        if MimeTypes.JSON.type in accept:
            content = await DataframeSerializerAsync().to_json(pdf, index=True, date_format='iso', orient=orient.value)
            return Response(content, media_type=MimeTypes.JSON.type)

        content = await DataframeSerializerAsync().to_parquet(pdf)
        return Response(content, media_type=MimeTypes.PARQUET.type)


async def set_bulk_field_and_send_record(ctx: Context, bulk_id, record, bulk_uri_access: BulkIdAccess):
    bulk_uri_access.set_bulk_uri(record=record, bulk_id=bulk_id)

    # push new version on the storage
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[record], data_partition_id=ctx.partition_id
    )


