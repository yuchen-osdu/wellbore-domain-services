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
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, status

from osdu.core.api.storage.exceptions import ResourceNotFoundException

from app.bulk_persistence import BulkReadFilters, GetDataParams, DataframeBasicDescribe
from app.model.osdu_record_id import split_record_id_version
from app.context import Context, get_ctx
from app.utils import OpenApiHandler
from app.helper.traces import TracingRoute, with_trace
from app.helper.logger import get_logger
from app.bulk_persistence import MAX_COLUMNS_RETURN

from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.common_parameters import (REQUEST_DATA_BODY_SCHEMA,
                                           REQUIRED_ROLES_READ,
                                           REQUIRED_ROLES_WRITE,
                                           json_orient_parameter,
                                           read_bulk_accept_type,
                                           write_bulk_content_type, response_404)

from ..record_utils import fetch_record
from ..dependency import FetchRecordPartialDependency, FetchRecordDependency, GetRecordFunction

from app.routers.bulk.bulk_uri_dependencies import get_bulk_id_access, BulkIdAccess
from app.routers.bulk.utils import (with_dask_blob_storage,
                                    get_df_validation_func,
                                    set_bulk_field_and_send_record,
                                    DataFrameRender,
                                    get_data_consistency_checks)
from app.routers.bulk.statistics_routes_dependencies import is_statistics_computation_enabled

# imports for session manipulation
from app.bulk_persistence import (
    SessionException,
    SessionState,
    SessionUpdateMode,
    SessionInternal,
    CommitSessionResponse
)

from app.routers.sessions import (
    UpdateSessionState,
    UpdateSessionStateValue,
    WithSessionStorages,
    get_session_dependencies,
)

# imports from bulk persistence
from app.bulk_persistence import (auto_cast_columns_to_string,
                                  DataFrameValidationFunc, no_validation,
                                  JSONOrient,
                                  get_dataframe, download_bulk,
                                  DaskBulkStorage,
                                  MimeTypes, MimeType,
                                  trace_dataframe_attributes, trace_attributes_root_span,
                                  BulkError, BulkRecordNotFound, FilterError, TooManyColumnsRequested,
                                  DataConsistencyChecks,
                                  BulkStatistics)

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
                    consistency_checks: DataConsistencyChecks = Depends(get_data_consistency_checks),
                    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
                    get_record: GetRecordFunction = Depends(FetchRecordDependency()),
                    stats_computation_enabled: bool = Depends(is_statistics_computation_enabled),
                    ):
    """
    Handle a post data outside a session. The given bulk will fully replace any existing one
    """
    record = await get_record(record_id, None)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)

    # process and store the data
    try:
        bulk_id, basic_describe = await dask_blob_storage.post_data_without_session(
            data=request.stream(),
            content_type=content_type,
            df_validator_func=df_validation_func,
            consistency_checks=consistency_checks,
            record=record)
    except BulkError as ex:
        ex.raise_as_http()

    trace_dataframe_attributes(basic_describe)

    # update record
    update_record_response = await set_bulk_field_and_send_record(ctx=ctx,
                                                                  bulk_id=bulk_id,
                                                                  record=record,
                                                                  bulk_uri_access=bulk_uri_access)

    if stats_computation_enabled:
        _, updated_record_version = split_record_id_version(update_record_response.record_id_versions[0])
        try:
            await BulkStatistics(dask_blob_storage).compute_bulk_statistics(record.id, bulk_id, updated_record_version)
        except Exception:
            get_logger().exception(f"Statistics computation failed for record '{record.id}' with bulk id '{bulk_id}'")

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
    responses={
        400: {"description": "Record not found"},
        **response_404
    }
)
async def post_chunk_data(record_id: str,
                          session_id: UUID,
                          request: Request,
                          content_type: MimeType = Depends(write_bulk_content_type),
                          with_session: WithSessionStorages = Depends(get_session_dependencies),
                          dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
                          df_validation_func: DataFrameValidationFunc = Depends(get_df_validation_func),
                          get_record: GetRecordFunction = Depends(FetchRecordDependency())
                          ) -> DataframeBasicDescribe:
    record = await get_record(record_id, None)
    if hasattr(request.state, 'version') and request.state.version != "V2":
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


# TODO: set bulk config when configuration is reloaded from environment
GET_DATA_DESCRIPTION = f"""  
Multiple media types response are available ("application/json", "application/x-parquet").  
The desired format can be specify in the "Accept" header, default is Parquet.  
When bulk statistics are requested using __describe__ query parameter, the response is always provided in JSON.  
The requested columns must not exceed {MAX_COLUMNS_RETURN}. The query parameter __curves__ can be use to limit the number of columns."""


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
    accept_type: MimeType = Depends(read_bulk_accept_type),
    orient: JSONOrient = Depends(json_orient_parameter),
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
    get_record: GetRecordFunction = Depends(FetchRecordPartialDependency())
):
    record = await get_record(record_id, version)
    if hasattr(request.state, 'version') and request.state.version != "V2":
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    try:
        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)  # TODO PATH logv2
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI') from e

    stat = None
    try:
        if not bulk_uri.is_valid():
            raise BulkRecordNotFound(record_id=record_id, bulk_id=None)
        bulk_id = bulk_uri.bulk_id
        bulk_filters = BulkReadFilters(data_param.get_bulk_filters())

        dask_blob_storage: DaskBulkStorage = await with_dask_blob_storage()
        future_index = None
        if bulk_uri.is_bulk_storage_V0():
            df = await get_dataframe(ctx, bulk_id)
            auto_cast_columns_to_string(df)
        else:
            if data_param.offset or data_param.limit:
                future_index = await DataFrameRender.load_index(record_id, bulk_id, dask_blob_storage)
            df, filters, stat = await _process_request_v1(record_id, bulk_id, data_param, bulk_filters, dask_blob_storage)

        df = await DataFrameRender.process_params(df, data_param, bulk_filters, dask_blob_storage, future_index)

        return await DataFrameRender.df_render(df, data_param, accept_type, orient=orient, stat=stat)
    except BulkError as ex:
        ex.raise_as_http()


@with_trace('_process_request_v1')
async def _process_request_v1(record_id: str,
                              bulk_id: str,
                              data_param: GetDataParams,
                              filters: BulkReadFilters,
                              dask_blob_storage: DaskBulkStorage):
    columns_to_load = None
    stat = await dask_blob_storage.read_stat(record_id, bulk_id)
    existing_col = set(stat['schema'])
    if data_param.curves:
        columns_to_load = DataFrameRender.get_matching_columns(data_param.get_curves_list(), existing_col)
        stat['schema'] = {k: stat['schema'][k] for k in columns_to_load}

    if not data_param.describe: # don't limit columns when describe parameter is True
        # if curves parameter is None, it means that we are going to load all existing columns
        nb_cols_to_return = len(columns_to_load) if columns_to_load else len(existing_col)
        if nb_cols_to_return > MAX_COLUMNS_RETURN:
            raise TooManyColumnsRequested(nb_cols_to_return, MAX_COLUMNS_RETURN)

    if filters.has_filter():
        # get column needed for filtering which are not yet in columns
        invalid_columns = filters.columns - existing_col
        if invalid_columns:
            raise FilterError(f'The columns:{list(invalid_columns)} to be filtered do not exist')
        if columns_to_load:
            columns_to_load = filters.columns.union(columns_to_load)

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
    accept_type: MimeType = Depends(read_bulk_accept_type),
    orient: JSONOrient = Depends(json_orient_parameter),
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
    get_record: GetRecordFunction = Depends(FetchRecordPartialDependency())
):
    return await get_data_version(record_id,
                                  None,
                                  request,
                                  ctrl_p,
                                  accept_type,
                                  orient,
                                  ctx,
                                  bulk_uri_access,
                                  get_record)


@router.patch(
    "/{record_id}/sessions/{session_id}",
    summary='Update a session, either commit or abandon.',
    responses={**response_404},
    response_model=CommitSessionResponse
)
async def complete_session(
    record_id: str,
    session_id: UUID,
    request: Request,
    update_request: UpdateSessionState,
    with_session: WithSessionStorages = Depends(get_session_dependencies),
    dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
    consistency_checks: DataConsistencyChecks = Depends(get_data_consistency_checks),
    stats_computation_enabled: bool = Depends(is_statistics_computation_enabled),
) -> CommitSessionResponse:
    tenant = with_session.tenant
    sessions_storage = with_session.sessions_storage

    try:
        # --------  SESSION COMMIT SEQUENCE -----------------------
        if update_request.state == UpdateSessionStateValue.Commit:
            async with sessions_storage.initiate_commit(tenant, record_id, session_id) as commit_guard:
                # get the session if some information is needed
                i_session = commit_guard.session
                _internal = i_session.internal  # <=  contains details, may be irrelevant or not needed

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
                                data=data,
                                content_type=content_type,
                                df_validator_func=no_validation,
                                consistency_checks=consistency_checks,
                                record=record)
                        except BulkError as ex:
                            ex.raise_as_http()
                        except ResourceNotFoundException:
                            BulkRecordNotFound(record_id=record_id, bulk_id=previous_bulk_id).raise_as_http()

                    else:
                        previous_bulk_id = previous_bulk_uri.bulk_id

                new_bulk_id = await dask_blob_storage.session_commit(i_session.session, previous_bulk_id)

                await consistency_checks.check_bulk_consistency_on_commit_session(record, new_bulk_id)
                # ==============>
                # ==============> UPDATE META DATA HERE (baseDepth, ...) <==============
                # ==============>
                new_record = await set_bulk_field_and_send_record(ctx, new_bulk_id, record, bulk_uri_access)

            i_session = commit_guard.session
            i_session.session.meta = i_session.session.meta or {}

            _, updated_version = split_record_id_version(new_record.record_id_versions[0])
            if updated_version is None:
                raise RuntimeError(f"{new_record.record_id_versions[0]} is not valid.")

            if stats_computation_enabled:
                try:
                    await BulkStatistics(dask_blob_storage).compute_bulk_statistics(record.id, new_bulk_id, updated_version)
                except Exception:
                    get_logger().exception(
                        f"Statistics computation failed for record '{record.id}' with bulk id '{new_bulk_id}'")

            response = CommitSessionResponse(
                **i_session.session.dict(exclude_unset=True, by_alias=True),
                version=updated_version
            )

            return response

        # --------  SESSION ABANDON SEQUENCE ----------------------
        if update_request.state == UpdateSessionStateValue.Abandon:
            async with sessions_storage.initiate_abandon(tenant, record_id, session_id) as abandon_guard:
                # get the session if some information is needed
                i_session: SessionInternal = abandon_guard.session
                internal = i_session.internal  # <=  contains details, may be irrelevant or not needed

                # ==============>
                # ==============> ADD ABANDON CODE HERE <==============
                # ==============>

            return CommitSessionResponse(
                **abandon_guard.session.session.dict(exclude_unset=True, by_alias=True)
            )

    except SessionException as ex:
        ex.raise_as_http()
    except BulkError as ex:
        ex.raise_as_http()
