# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from typing import List, Set, Optional
import re
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
import pandas as pd

from app.bulk_persistence import DataframeSerializerAsync, JSONOrient
from app.bulk_persistence.bulk_id import BulkId
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.errors import BulkError, BulkNotFound
from app.clients.storage_service_client import get_storage_record_service
from app.record_utils import fetch_record
from app.bulk_persistence.mime_types import MimeTypes
from app.model.model_chunking import GetDataParams
from app.utils import Context, OpenApiHandler, get_ctx
from app.persistence.sessions_storage import (Session, SessionException, SessionState, SessionUpdateMode)
from app.routers.common_parameters import (
    REQUEST_DATA_BODY_SCHEMA,
    REQUIRED_ROLES_READ,
    REQUIRED_ROLES_WRITE,
    json_orient_parameter)
from app.routers.sessions import (SessionInternal, UpdateSessionState, UpdateSessionStateValue,
                                  WithSessionStorages, get_session_dependencies)


router_bulk = APIRouter()  # router dedicated to bulk APIs


BULK_URN_PREFIX_VERSION = "wdms-1"
BULK_URI_FIELD = "bulkURI"


async def get_df_from_request(request: Request, orient: Optional[str] = None) -> pd.DataFrame:
    """ extract dataframe from request """

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
            return await DataframeSerializerAsync().read_json(content, orient)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail='invalid body')  # TODO

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f'Invalid content-type, "{ct}" is not supported')


async def with_dask_blob_storage() -> DaskBulkStorage:
    ctx = Context.current()
    return await ctx.app_injector.get(DaskBulkStorage)


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
        if m_sel and m_sel['stop']: 
            with suppress(ValueError):  # suppress int conversion exceptions
                if int(m_sel['start']) <=  int(m_col['start']) <= int(m_sel['stop']):
                    return True
        return False
    
    @staticmethod
    def get_matching_column(selection: List[str], cols: Set[str]) -> List[str]:
        selected = set()
        for sel in selection:
            selected.update(filter(lambda col: DataFrameRender._col_matching(sel, col),
                                   cols.difference(selected)))
        return list(selected)

    @staticmethod
    async def process_params(df, params: GetDataParams):
        if params.curves:
            selection = list(map(str.strip, params.curves.split(',')))
            columns = DataFrameRender.get_matching_column(selection, set(df))
            df = df[sorted(columns)]

        if params.offset:
            head_index = df.head(params.offset, npartitions=-1, compute=False).index
            index = await DataFrameRender.compute(head_index)  # TODO could be slow!
            df = df.loc[~df.index.isin(index)]

        if params.limit and params.limit > 0:
            try:
                df = df.head(params.limit, npartitions=-1, compute=False)  # dask async
            except:
                df = df.head(params.limit)
        return df

    @staticmethod
    async def df_render(df, params: GetDataParams, accept: str = None):
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
            return Response(pdf.to_json(index=True, date_format='iso'), media_type=MimeTypes.JSON.type)

        if MimeTypes.CSV.type in accept:
            return Response(pdf.to_csv(), media_type=MimeTypes.CSV.type)

        # in any other case => Parquet anyway?
        return Response(pdf.to_parquet(engine="pyarrow"), media_type=MimeTypes.PARQUET.type)


def get_bulk_uri(record):
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


@OpenApiHandler.set(operation_id="post_data", request_body=REQUEST_DATA_BODY_SCHEMA)
@router_bulk.post(
    '/{record_id}/data',
    summary='Writes data as a whole bulk, creates a new version.',
    description="""
Writes data to the associated record. It creates a new version.
Payload is expected to contain the entire bulk which will replace as latest version
any previous bulk. Previous bulk versions are accessible via the get bulk data version API.
Support JSON and Parquet format ('Content_Type' must be set accordingly).
In case of JSON the orient must be set accordingly. Support http chunked encoding transfer.
""" + REQUIRED_ROLES_WRITE,
    operation_id="write_record_data",
    responses={
            404: {},
            200: {}
        })
async def post_data(record_id: str,
                    request: Request,
                    orient: JSONOrient = Depends(json_orient_parameter),
                    ctx: Context = Depends(get_ctx),
                    dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
                    ):
    async def save_blob():
        df = await get_df_from_request(request, orient)
        return await dask_blob_storage.save_blob(df, record_id)

    record, bulk_id = await asyncio.gather(
        fetch_record(ctx, record_id),
        save_blob()
    )
    return await set_bulk_field_and_send_record(ctx=ctx, bulk_id=bulk_id, record=record)


@OpenApiHandler.set(operation_id="post_chunk_data", request_body=REQUEST_DATA_BODY_SCHEMA)
@router_bulk.post(
    "/{record_id}/sessions/{session_id}/data",
    summary="Send a data chunk. Session must be complete/commit once all chunks are sent.",
    description="Send a data chunk. Session must be complete/commit once all chunks are sent. "
                "This will create a new and single version aggregating all and previous bulk."
                "Support JSON and Parquet format ('Content_Type' must be set accordingly). "
                "In case of JSON the orient must be set accordingly. Support http chunked encoding."
    + REQUIRED_ROLES_WRITE,
    operation_id="post_chunk_data",
    responses={400: {"error": "Record not found"}}
)
async def post_chunk_data(record_id: str,
                          session_id: str,
                          request: Request,
                          orient: JSONOrient = Depends(json_orient_parameter),
                          with_session: WithSessionStorages = Depends(get_session_dependencies),
                          dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
                          ):
    i_session = await with_session.get_session(record_id, session_id)
    if i_session.session.state != SessionState.Open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session cannot accept data, state={i_session.session.state}")

    df = await get_df_from_request(request, orient)
    await dask_blob_storage.session_add_chunk(i_session.session, df)


@router_bulk.get(
    '/{record_id}/versions/{version}/data',
    summary='Returns data of the specified version.',
    description='Returns the data of a specific version according to the specified query parameters.'
    ' Multiple media types response are available ("application/json", text/csv", "application/x-parquet")'
    ' The desired format can be specify in "Accept" header. The default is Parquet.'
    ' When bulk statistics are requested using "describe" parameter, the response is always provided in JSON'
    + REQUIRED_ROLES_READ,
    # response_model=RecordData,
    responses={
        404: {},
        200: {"content": {
            MimeTypes.JSON.type: {},
            MimeTypes.PARQUET.type: {},
            MimeTypes.CSV.type: {},
        }}
    }
)
async def get_data_version(
    record_id: str, version: int,
    request: Request,
    ctrl_p: GetDataParams = Depends(),
    ctx: Context = Depends(get_ctx),
    dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
):
    record = await fetch_record(ctx, record_id, version)
    bulk_uri = get_bulk_uri(record)
    if bulk_uri is None:
        raise BulkNotFound(record_id=record_id, bulk_id=None)
    bulk_id, prefix = BulkId.bulk_urn_decode(bulk_uri)
    try:
        if prefix != BULK_URN_PREFIX_VERSION:
            raise BulkNotFound(record_id=record_id, bulk_id=bulk_id)
        df = await dask_blob_storage.load_bulk(record_id, bulk_id)
        df = await DataFrameRender.process_params(df, ctrl_p)

        return await DataFrameRender.df_render(df, ctrl_p, request.headers.get('Accept'))
    except BulkError as ex:
        ex.raise_as_http()


@router_bulk.get(
    "/{record_id}/data",
    summary='Returns the data according to the specified query parameters.',
    description='Returns the data according to the specified query parameters.'
    ' Multiple media types response are available ("application/json", text/csv", "application/x-parquet").'
    ' The desired format can be specify in "Accept" header. The default is Parquet.'
    ' When bulk statistics are requested using "describe" parameter, the response is always provided in JSON.'
    + REQUIRED_ROLES_READ,
    # response_model=Union[RecordData, Dict],
    responses={
        404: {},
        200: {"content": {
            MimeTypes.JSON.type: {},
            MimeTypes.PARQUET.type: {},
            MimeTypes.CSV.type: {},
        }}
    }
)
async def get_data(
    record_id: str,
    request: Request,
    ctrl_p: GetDataParams = Depends(),
    ctx: Context = Depends(get_ctx),
    dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
):
    return await get_data_version(record_id, None, request, ctrl_p, ctx, dask_blob_storage)


@router_bulk.patch(
    "/{record_id}/sessions/{session_id}",
    summary='Update a session, either commit or abandon.',
    response_model=Session
)
async def complete_session(
    record_id: str,
    session_id: str,
    update_request: UpdateSessionState,
    with_session: WithSessionStorages = Depends(get_session_dependencies),
    dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
    ctx: Context = Depends(get_ctx),
) -> Session:
    tenant = with_session.tenant
    sessions_storage = with_session.sessions_storage

    try:
        # --------  SESSION COMMIT SEQUENCE -----------------------
        if update_request.state == UpdateSessionStateValue.Commit:
            async with sessions_storage.initiate_commit(tenant, record_id, session_id) as commit_guard:
                # get the session if some information is needed
                i_session = commit_guard.session
                internal = i_session.internal  # <=  contains details details, may be irrelevant or not needed

                record = await fetch_record(ctx, record_id, i_session.session.fromVersion)
                previous_bulk_uri = None
                bulk_urn = get_bulk_uri(record)
                if i_session.session.mode == SessionUpdateMode.Update and bulk_urn is not None:
                    previous_bulk_uri, _prefix = BulkId.bulk_urn_decode(bulk_urn)

                new_bulk_uri = await dask_blob_storage.session_commit(i_session.session, previous_bulk_uri)
                # ==============>
                # ==============> UPDATE WELLLOG META DATA HERE (baseDepth, ...) <==============
                # ==============>
                await set_bulk_field_and_send_record(ctx, new_bulk_uri, record)

            i_session = commit_guard.session
            i_session.session.meta = i_session.session.meta or {}
            i_session.session.meta.update({"some_detail_about_merge": "like the shape, number of rows ..."})
            return i_session.session

        # --------  SESSION ABANDON SEQUENCE ----------------------
        if update_request.state == UpdateSessionStateValue.Abandon:
            async with sessions_storage.initiate_abandon(tenant, record_id, session_id) as abandon_guard:
                # get the session if some information is needed
                i_session: SessionInternal = abandon_guard.session
                internal = i_session.internal  # <=  contains details details, may be irrelevant or not needed

                # ==============>
                # ==============> ADD ABANDON CODE HERE <==============
                # ==============>

            return abandon_guard.session.session

    except SessionException as ex:
        ex.raise_as_http()
    except BulkError as ex:
        ex.raise_as_http()
