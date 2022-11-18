from typing import List, Set, Optional, Iterable
import ast
from natsort import natsorted
from contextlib import suppress

from fastapi import HTTPException, Request, status
from fastapi.routing import APIRoute
from fastapi.responses import Response
import dask.dataframe as dd
import pandas as pd
from pyarrow.lib import ArrowInvalid

from app.bulk_persistence import DaskBulkStorage, DataframeSerializerAsync, \
    MimeTypes, MimeType, JSONOrient, trace_dataframe_attributes, capture_timings, \
    auto_cast_columns_to_string, columns_type_must_be_string, \
    no_validation, DataFrameValidationFunc, \
    FilterError, internal_bulk_exceptions, BulkCurvesNotFound
from app.clients.storage_service_client import get_storage_record_service
from app.context import get_ctx, Context
from app.utils import OpenApiHandler
from app.helper.traces import with_trace
from app.bulk_persistence import BulkReadFilterOperator, BulkReadFilters, GetDataParams, DataframeDescribe
from app.bulk_persistence.dataframe_columns import select_columns
from app.routers.bulk.bulk_uri_dependencies import BulkIdAccess

from app.consistency import NoConsistencyChecks, WelllogDataConsistencyChecks, TrajectoryDataConsistencyChecks


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
    if not getattr(request.state, 'check_input_df_func', None):
        return no_validation
    return request.state.check_input_df_func


def set_welllog_data_consistency_check(request: Request):
    request.state.data_consistency_checks = WelllogDataConsistencyChecks()


def set_trajectory_data_consistency_check(request: Request):
    request.state.data_consistency_checks = TrajectoryDataConsistencyChecks()


def get_data_consistency_checks(request: Request):
    if not getattr(request.state, 'data_consistency_checks', None):
        return NoConsistencyChecks()
    return request.state.data_consistency_checks


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
    async def get_size(df):
        if isinstance(df, pd.DataFrame):
            return len(df.index)
        driver = await with_dask_blob_storage()
        return await driver._submit_with_trace(len, df.index)

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

    @staticmethod
    @with_trace('get_matching_column')
    def get_matching_columns(selection: List[str], cols: Set[str]) -> List[str]:
        matching_columns, curves_non_existent = select_columns(selection, cols)
        if curves_non_existent:
            raise BulkCurvesNotFound(curves=curves_non_existent)

        return matching_columns

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
    async def df_render(df, params: GetDataParams,
                        render_type: Optional[MimeType] = None,
                        orient: Optional[JSONOrient] = None,
                        columns: Optional[Iterable[str]] = None):
        if params.describe:
            nb_rows = await DataFrameRender.get_size(df)
            if params.curves is None and columns:
                columns = natsorted(list(columns))
            else:
                columns = list(df.columns)

            return DataframeDescribe(
                numberOfRows=nb_rows,
                columns=columns
            )

        pdf = await DataFrameRender.compute(df)
        pdf.index.name = None  # TODO
        trace_dataframe_attributes(pdf)

        if render_type == MimeTypes.PARQUET:
            content = await DataframeSerializerAsync().to_parquet(pdf)
            return Response(content, media_type=render_type.type)

        if render_type == MimeTypes.JSON:
            content = await DataframeSerializerAsync().to_json(pdf, index=True, date_format='iso', orient=orient.value)
            return Response(content, media_type=render_type.type)

        raise ValueError("Invalid render type")


async def set_bulk_field_and_send_record(ctx: Context, bulk_id, record, bulk_uri_access: BulkIdAccess):
    bulk_uri_access.set_bulk_uri(record=record, bulk_id=bulk_id)

    # push new version on the storage
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[record], data_partition_id=ctx.partition_id
    )
