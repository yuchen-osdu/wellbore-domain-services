from fastapi import HTTPException, Request, status
from fastapi.routing import APIRoute

from typing import List, Set, Optional
import re
from contextlib import suppress
from fastapi.responses import Response
import dask.dataframe as dd
import pandas as pd
from natsort import natsorted

from app.clients.storage_service_client import get_storage_record_service
from app.bulk_persistence import DataframeSerializerAsync
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.mime_types import MimeTypes
from app.bulk_persistence import BulkId, JSONOrient
from app.utils import get_ctx, OpenApiHandler, Context
from app.helper.traces import with_trace

from app.model.model_chunking import GetDataParams

BULK_URN_PREFIX_VERSION = "wdms-1"
BULK_URI_FIELD = "bulkURI"


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
    request.state.check_input_df_func = _check_df_columns_type


async def set_legacy_input_dataframe_check(request: Request):
    """
    Inject into request state (c.f. https://www.starlette.io/requests/#other-state) the check function.
    For legacy routes, the check function is set according to content-type:
        - parquet: no backward compatibility required, same function that v3 bulk
        - json: backward compatibility required, the check function will cast column name type as string
     """
    content_type = request.headers.get('Content-Type')
    if content_type == 'application/x-parquet':
        request.state.check_input_df_func = _check_df_columns_type
    else:
        request.state.check_input_df_func = _check_df_columns_type_legacy


def get_check_input_df_func(request: Request):
    """
    Retrieve from request state (c.f. https://www.starlette.io/requests/#other-state) the injected input check function.
    This function is injected when mounting the bulk router into the fastApi app as router's 'dependencies'
    in module app/wdms_app.

    NOTE: attribute name 'check_input_df_func' which contains the function should be IDENTICAL
    that defined in above functions
    """
    if not request.state.check_input_df_func:
        return lambda x: True
    return request.state.check_input_df_func


def _check_df_columns_type_legacy(df: pd.DataFrame):
    """ If given dataframe contains columns name which is not a string, cast it  """
    if any((type(t) is not str for t in df.columns)):
        get_ctx().logger.warning("_check_df_columns_type_legacy() - df columns type casted")
        df.columns = map(str, df.columns)
    return True


def _check_df_columns_type(df: pd.DataFrame):
    """ Ensure given dataframe contains columns name as string only as described by WellLog schemas """
    if any((type(t) is not str for t in df.columns)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f'All columns type should be string')
    return True


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
    @with_trace('process_params')
    async def process_params(df, params: GetDataParams):
        if isinstance(df, pd.DataFrame):
            df = dd.from_pandas(df, npartitions=1)

        if params.curves:
            selection = list(map(str.strip, params.curves.split(',')))
            columns = DataFrameRender.get_matching_column(selection, set(df))
            df = df[columns]  # columns are ordered as the user requested
        else:
            df = df[natsorted(df.columns)]  # columns are ordered by natural sort

        if params.offset:
            head_index = df.head(params.offset, npartitions=-1, compute=False).index
            index = await DataFrameRender.compute(head_index)  # TODO could be slow!
            df = df.loc[~df.index.isin(index)]

        if params.limit and params.limit > 0:
            df = df.head(params.limit, npartitions=-1, compute=False)

        return df


    @staticmethod
    @with_trace('df_render')
    async def df_render(df, params: GetDataParams, accept: str = None, orient: Optional[JSONOrient] = None):
        if params.describe:
            return {
                "numberOfRows": await DataFrameRender.get_size(df),
                "columns": [c for c in df.columns]
            }

        pdf = await DataFrameRender.compute(df)
        pdf.index.name = None  # TODO

        if not accept or MimeTypes.PARQUET.type in accept:
            return Response(pdf.to_parquet(engine="pyarrow"), media_type=MimeTypes.PARQUET.type)

        if MimeTypes.JSON.type in accept:
            return Response(
                pdf.to_json(index=True, date_format='iso', orient=orient.value), media_type=MimeTypes.JSON.type
            )

        if MimeTypes.CSV.type in accept:
            return Response(pdf.to_csv(), media_type=MimeTypes.CSV.type)

        # in any other case => Parquet anyway?
        return Response(pdf.to_parquet(engine="pyarrow"), media_type=MimeTypes.PARQUET.type)


def get_bulk_uri_osdu(record):
    return record.data.get('ExtensionProperties', {}).get('wdms', {}).get(BULK_URI_FIELD, None)


def set_bulk_uri(record, bulk_urn):
    return record.data.update({'ExtensionProperties': {'wdms': {BULK_URI_FIELD: bulk_urn}}})


async def set_bulk_field_and_send_record(ctx: Context, bulk_id, record):
    bulk_urn = BulkId.bulk_urn_encode(bulk_id, BULK_URN_PREFIX_VERSION)
    set_bulk_uri(record, bulk_urn)

    # push new version on the storage
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[record], data_partition_id=ctx.partition_id
    )
