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

from app.bulk_persistence.dask.errors import FilterError
from app.bulk_persistence.dataframe_validators import auto_cast_columns_to_string, columns_type_must_be_string, \
    no_validation, DataFrameValidationFunc
from app.clients.storage_service_client import get_storage_record_service
from app.bulk_persistence import DataframeSerializerAsync
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.utils import set_index
from app.bulk_persistence.mime_types import MimeTypes
from app.bulk_persistence import JSONOrient
from app.utils import get_ctx, OpenApiHandler, Context
from app.helper.traces import with_trace
from app.model.model_chunking import GetDataParams
from app.routers.bulk.bulk_uri_dependencies import (BulkIdAccess, BULK_URI_FIELD)


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
    if content_type == 'application/x-parquet':
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
async def get_df_from_request(request: Request, orient: Optional[str] = None) -> pd.DataFrame:
    """ Extract dataframe from request """

    ct = request.headers.get('Content-Type', '')
    if MimeTypes.PARQUET.match(ct):
        content = await request.body()  # request.stream()
        try:
            return await DataframeSerializerAsync().read_parquet(content)
        except OSError as err:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f'{err}')  # TODO

    if MimeTypes.JSON.match(ct):
        content = await request.body()  # request.stream()
        try:
            return await DataframeSerializerAsync().read_json(content, orient, convert_axes=False)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail='invalid body')  # TODO

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f'Invalid content-type, "{ct}" is not supported')


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
        return await driver.client.submit(lambda: len(df.index))

    @staticmethod
    async def select_range(df: dd.DataFrame, offset, limit):
        if offset or limit:
            driver = await with_dask_blob_storage()
            df = driver.client.persist(df)
            df = await driver.client.submit(set_index, df)
            index = await driver.client.submit(lambda x: x.index.compute(), df)
            if offset and offset > 0:
                index = index[offset:]
            if limit and limit > 0:
                index = index[:limit]
            return df.loc[df.index.isin(index)]
        return df

    re_array_selection = re.compile(r'^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$')

    @staticmethod
    def _col_matching(sel, col):
        if sel == col:  # exact match
            return True
        m_col = DataFrameRender.re_array_selection.match(col)
        if not m_col:  # if the column doesn't have an array pattern (col[*])
            return False
        # compare selection with curve name without array suffix [*]
        if sel == m_col['name']:  # if selection is 'c', c[*] should match
            return True
        # range selection use cases c[0:2] should match c[0], c[1] and c[2]
        m_sel = DataFrameRender.re_array_selection.match(sel)
        if m_sel and m_sel['stop'] and m_sel['name'] == m_col['name']:
            with suppress(ValueError):  # suppress int conversion exceptions
                if int(m_sel['start']) <= int(m_col['start']) <= int(m_sel['stop']):
                    return True
        return False

    @staticmethod
    def get_matching_column(selection: List[str], cols: Set[str]) -> List[str]:
        selected = []
        for sel in selection:
            matching_columns = list(filter(lambda col: DataFrameRender._col_matching(sel, col),
                                           cols.difference(selected)))
            selected.extend(natsorted(matching_columns))
        return selected


    @staticmethod
    def apply_filter(df, filters):

        operator_to_function = {
            'eq' : lambda df, col, val : df[col] == val,
            'neq' : lambda df, col, val : df[col] != val,
            'lte': lambda df, col, val : df[col] <= val,
            'lt': lambda df, col, val : df[col] < val,
            'gt': lambda df, col, val : df[col] > val,
            'gte': lambda df, col, val : df[col] >= val,
            'in': lambda df, col, val : df[col].isin(val)
        }
        for col_name, operation in filters.items():
            for operator, value in operation.items():
                try:
                    new_value = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    new_value = value
                if df[col_name].dtype == object:
                    if isinstance(new_value, tuple):
                        new_value = [str(v) for v in new_value]
                    else:
                        new_value = str(new_value)

                filter_function = operator_to_function[operator]
                try:
                    df = df.loc[filter_function(df, col_name, new_value)]
                except ValueError:
                    raise FilterError('the value is not valid for this operation')
        return df

    @staticmethod
    @with_trace('process_params')
    async def process_params(df, params: GetDataParams, filters):
        # pass filters as a parameter here to avoid using params.get_filter() to parse filters 2 times
        if isinstance(df, pd.DataFrame):
            df = dd.from_pandas(df, npartitions=1)

        if filters:
            df = DataFrameRender.apply_filter(df, filters)

        if params.curves:
            selection = list(map(str.strip, params.curves.split(',')))
            columns = DataFrameRender.get_matching_column(selection, set(df))
            df = df[columns]  # columns are ordered as the user requested
        else:
            df = df[natsorted(df.columns)]  # columns are ordered by natural sort

        df = await DataFrameRender.select_range(df, params.offset, params.limit)

        return df

    @staticmethod
    @with_trace('df_render')
    async def df_render(df, params: GetDataParams, accept: str = None, orient: Optional[JSONOrient] = None, stat=None):
        if params.describe:
            if stat and not params.limit and not params.offset:
                nb_rows = stat['num_rows']
                columns = natsorted(list(stat['schema']))
            else:
                nb_rows = await DataFrameRender.get_size(df)
                columns = list(df.columns)

            return {
                "numberOfRows": nb_rows,
                "columns": columns
            }

        pdf = await DataFrameRender.compute(df)
        pdf.index.name = None  # TODO

        if not accept or MimeTypes.PARQUET.type in accept:
            content = await DataframeSerializerAsync().to_parquet(pdf, engine="pyarrow")
            return Response(content, media_type=MimeTypes.PARQUET.type)

        if MimeTypes.JSON.type in accept:
            content = await DataframeSerializerAsync().to_json(pdf, index=True, date_format='iso', orient=orient.value)
            return Response(content, media_type=MimeTypes.JSON.type)

        if MimeTypes.CSV.type in accept:
            content = await DataframeSerializerAsync().to_csv(pdf)
            return Response(content, media_type=MimeTypes.CSV.type)

        content = await DataframeSerializerAsync().to_parquet(pdf, engine="pyarrow")
        return Response(content, media_type=MimeTypes.PARQUET.type)


async def set_bulk_field_and_send_record(ctx: Context, bulk_id, record, bulk_uri_access: BulkIdAccess):
    bulk_uri_access.set_bulk_uri(record=record, bulk_id=bulk_id)

    # push new version on the storage
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[record], data_partition_id=ctx.partition_id
    )
