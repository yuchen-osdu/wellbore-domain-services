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

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, status

from osdu.core.api.storage.exceptions import ResourceNotFoundException

from app.model.model_chunking import GetDataParams, DataframeBasicDescribe
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.utils import Context, OpenApiHandler, get_ctx
from app.helper.traces import TracingRoute, with_trace
from app.routers.common_parameters import (REQUEST_DATA_BODY_SCHEMA,
                                           REQUIRED_ROLES_READ,
                                           REQUIRED_ROLES_WRITE,
                                           json_orient_parameter,
                                           write_bulk_content_type)

from app.conf import Config
from app.routers.record_utils import fetch_record
from app.routers.bulk.bulk_uri_dependencies import get_bulk_id_access, BulkIdAccess
from app.routers.bulk.utils import (with_dask_blob_storage,
                                    get_df_validation_func,
                                    set_bulk_field_and_send_record,
                                    DataFrameRender)

# imports for session manipulation
from app.persistence.sessions_storage import (Session, SessionException, SessionState, SessionUpdateMode)
from app.routers.sessions import (SessionInternal,
                                  UpdateSessionState,
                                  UpdateSessionStateValue,
                                  WithSessionStorages,
                                  get_session_dependencies)

# imports from bulk persistence
from app.bulk_persistence.dataframe_validators import (auto_cast_columns_to_string,
                                                       DataFrameValidationFunc,
                                                       no_validation)
from app.bulk_persistence import JSONOrient, get_dataframe, download_bulk
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.errors import BulkError, BulkRecordNotFound, FilterError, TooManyColumnsRequested
from app.bulk_persistence.mime_types import MimeTypes, MimeType
from app.bulk_persistence.dask.traces import trace_dataframe_attributes, trace_attributes_root_span

router = APIRouter(route_class=TracingRoute)  # router dedicated to bulk APIs

OPERATION_IDS = {"record_data": "write_record_data",
                 "chunk_data": "post_chunk_data"}


@OpenApiHandler.set(operation_id=OPERATION_IDS["record_data"], request_body=REQUEST_DATA_BODY_SCHEMA)
@router.post(
    '/{record_id}/data',
    summary='Writes data as a whole bulk, creates a new version.',
    description="""
Writes data to the associated record. It creates a new version.
Payload is expected to contain the entire bulk which will replace as latest version
any previous bulk. Previous bulk versions are accessible via the get bulk data version API.
Support JSON and Parquet format ('Content_Type' must be set accordingly).
Support http chunked encoding transfer.
""" + REQUIRED_ROLES_WRITE,
    operation_id=OPERATION_IDS["record_data"],
    responses={
            404: {},
            200: {}
        })
async def post_data(record_id: str,
                    request: Request,
                    content_type: MimeType = Depends(write_bulk_content_type),
                    ctx: Context = Depends(get_ctx),
                    dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
                    df_validation_func: DataFrameValidationFunc = Depends(get_df_validation_func),
                    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)):

    """
    Handle a post data outside of a session. The given bulk will fully replace any existing one
    """
    record = await fetch_record(ctx, record_id)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)

    # process and store the data
    try:
        bulk_id, basic_describe = await dask_blob_storage.post_data_without_session(
            request.stream(),
            content_type,
            df_validation_func,
            record_id)

    except BulkError as ex:
        ex.raise_as_http()

    trace_dataframe_attributes(basic_describe)

    # update record
    update_record_response = await set_bulk_field_and_send_record(ctx=ctx,
                                                                  bulk_id=bulk_id,
                                                                  record=record,
                                                                  bulk_uri_access=bulk_uri_access)
    return update_record_response
    # TODO proposal: adding basic describe of data that has been stored
    # return PostDataResponse(**update_record_response.dict(exclude_unset=True, by_alias=True), dataStat=basic_describe)


@OpenApiHandler.set(operation_id=OPERATION_IDS["chunk_data"], request_body=REQUEST_DATA_BODY_SCHEMA)
@router.post(
    "/{record_id}/sessions/{session_id}/data",
    summary="Send a data chunk. Session must be complete/commit once all chunks are sent.",
    description="Send a data chunk. Session must be complete/commit once all chunks are sent. "
                "This will create a new and single version aggregating all and previous bulk."
                "Support JSON and Parquet format ('Content_Type' must be set accordingly). "
                "Support http chunked encoding."
    + REQUIRED_ROLES_WRITE,
    operation_id=OPERATION_IDS["chunk_data"],
    response_model=DataframeBasicDescribe,
    responses={400: {"description": "Record not found"}}
)
async def post_chunk_data(record_id: str,
                          session_id: str,
                          request: Request,
                          content_type: MimeType = Depends(write_bulk_content_type),
                          with_session: WithSessionStorages = Depends(get_session_dependencies),
                          dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
                          df_validation_func: DataFrameValidationFunc = Depends(get_df_validation_func)
                          ) -> DataframeBasicDescribe:
    if hasattr(request.state, 'version') and request.state.version != "V2":
        record = await fetch_record(with_session.ctx, record_id)
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)

    # fetch the session
    i_session = await with_session.get_session(record_id, session_id)
    if i_session.session.state != SessionState.Open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session cannot accept data, state={i_session.session.state}")

    # process and store the data chunk
    try:
        bulk_id, basic_describe = await dask_blob_storage.add_chunk_in_session(
            request.stream(),
            content_type,
            df_validation_func,
            record_id,
            i_session.session.id)

        trace_dataframe_attributes(basic_describe)
        return basic_describe

    except BulkError as ex:
        ex.raise_as_http()


GET_DATA_DESCRIPTION = f"""  
Multiple media types response are available ("application/json", "application/x-parquet").  
The desired format can be specify in the "Accept" header, default is Parquet.  
When bulk statistics are requested using __describe__ query parameter, the response is always provided in JSON.  
The requested columns must not exceed {Config.max_columns_return.value}. The query parameter __curves__ can be use to limit the number of columns."""


@router.get(
    '/{record_id}/versions/{version}/data',
    summary='Returns data of the specified version.',
    description='Returns the data of a specific version according to the specified query parameters.'
    + GET_DATA_DESCRIPTION
    + REQUIRED_ROLES_READ,
    # response_model=RecordData,
    responses={
        404: {},
        200: {"content": {
            MimeTypes.JSON.type: {},
            MimeTypes.PARQUET.type: {},
        }}
    }
)
async def get_data_version(
    record_id: str, version: int,
    request: Request,
    data_param: GetDataParams = Depends(),
    orient: JSONOrient = Depends(json_orient_parameter),
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
):
    record = await fetch_record(ctx, record_id, version)
    if hasattr(request.state, 'version') and request.state.version != "V2":
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    try:
        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)  # TODO PATH logv2
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI') from e

    filters = None
    stat = None
    try:
        if not bulk_uri.is_valid():
            raise BulkRecordNotFound(record_id=record_id, bulk_id=None)
        bulk_id = bulk_uri.bulk_id
        if bulk_uri.is_bulk_storage_V0():
            df = await get_dataframe(ctx, bulk_id)
            auto_cast_columns_to_string(df)
        else:
            df, filters, stat = await _process_request_v1(record_id, bulk_id, data_param, filters)

        df = await DataFrameRender.process_params(df, data_param, filters=filters)
        return await DataFrameRender.df_render(df, data_param, request.headers.get('Accept'), orient=orient, stat=stat)
    except BulkError as ex:
        ex.raise_as_http()


@with_trace('_process_request_v1')
async def _process_request_v1(record_id: str, bulk_id: str, data_param: GetDataParams, filters):
    dask_blob_storage: DaskBulkStorage = await with_dask_blob_storage()
    columns_to_load = None
    stat = await dask_blob_storage.read_stat(record_id, bulk_id)
    existing_col = set(stat['schema'])
    if data_param.curves:
        columns_to_load = DataFrameRender.get_matching_column(data_param.get_curves_list(), existing_col)
        stat['schema'] = {k: stat['schema'][k] for k in columns_to_load}

    if not data_param.describe: # don't limit columns when describe parameter is True
        # if curves parameter is None, it means that we are going to load all existing columns
        nb_cols_to_return = len(columns_to_load) if columns_to_load else len(existing_col)
        if nb_cols_to_return > Config.max_columns_return.value:
            raise TooManyColumnsRequested(nb_cols_to_return)

    if data_param.bulk_filter:
        # get column needed for filtering which are not yet in columns
        filters = data_param.get_filters()
        invalid_columns = filters.keys() - existing_col
        if invalid_columns:
            raise FilterError(f'The columns:{list(invalid_columns)} to be filtered do not exist')
        if columns_to_load:
            columns_to_load.extend(filters)
            columns_to_load = set(columns_to_load)
    if columns_to_load is None and data_param.describe:
        # optimization: create a fake dataset when describe on all columns
        index = await dask_blob_storage.load_index(record_id, bulk_id)
        df = pd.DataFrame(index=index)
    else:
        # loading the dataframe with filter on columns is faster than filtering columns on df
        df = await dask_blob_storage.load_bulk(record_id, bulk_id, columns=columns_to_load)
    return df, filters, stat


@router.get(
    "/{record_id}/data",
    summary='Returns the data according to the specified query parameters.',
    description='Returns the data according to the specified query parameters.'
    + GET_DATA_DESCRIPTION
    + REQUIRED_ROLES_READ,
    # response_model=Union[RecordData, Dict],
    responses={
        404: {},
        200: {"content": {
            MimeTypes.JSON.type: {},
            MimeTypes.PARQUET.type: {},
        }}
    }
)
async def get_data(
    record_id: str,
    request: Request,
    ctrl_p: GetDataParams = Depends(),
    orient: JSONOrient = Depends(json_orient_parameter),
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
):
    return await get_data_version(record_id, None, request, ctrl_p, orient, ctx, bulk_uri_access)


@router.patch(
    "/{record_id}/sessions/{session_id}",
    summary='Update a session, either commit or abandon.',
    response_model=Session
)
async def complete_session(
    record_id: str,
    session_id: str,
    request: Request,
    update_request: UpdateSessionState,
    with_session: WithSessionStorages = Depends(get_session_dependencies),
    dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
) -> Session:
    tenant = with_session.tenant
    sessions_storage = with_session.sessions_storage

    try:
        # --------  SESSION COMMIT SEQUENCE -----------------------
        if update_request.state == UpdateSessionStateValue.Commit:
            async with sessions_storage.initiate_commit(tenant, record_id, session_id) as commit_guard:
                # get the session if some information is needed
                i_session = commit_guard.session
                _internal = i_session.internal  # <=  contains details details, may be irrelevant or not needed

                trace_attributes_root_span({'session-mode': i_session.session.mode})

                record = await fetch_record(ctx, record_id, i_session.session.fromVersion)
                DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
                previous_bulk_id = None

                if i_session.session.mode == SessionUpdateMode.Update:

                    try:
                        previous_bulk_uri = bulk_uri_access.get_bulk_uri(record)  # TODO PATH logv2
                    except ValueError:
                        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                            detail=f'Record with version {i_session.session.fromVersion} from which '
                                                   f'update contains an invalid bulk URI')

                    if previous_bulk_uri.is_bulk_storage_V0():
                        try:
                            data, content_type = await download_bulk(ctx, previous_bulk_uri.bulk_id)
                            # convert old bulk to new one
                            previous_bulk_id, _ = await dask_blob_storage.post_data_without_session(
                                data,
                                content_type,
                                no_validation,
                                record_id)
                        except BulkError as ex:
                            ex.raise_as_http()
                        except ResourceNotFoundException:
                            BulkRecordNotFound(record_id=record_id, bulk_id=previous_bulk_id).raise_as_http()

                    else:
                        previous_bulk_id = previous_bulk_uri.bulk_id

                new_bulk_id = await dask_blob_storage.session_commit(i_session.session, previous_bulk_id)
                # ==============>
                # ==============> UPDATE META DATA HERE (baseDepth, ...) <==============
                # ==============>
                await set_bulk_field_and_send_record(ctx, new_bulk_id, record, bulk_uri_access)

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
