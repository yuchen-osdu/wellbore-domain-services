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

from app.bulk_persistence.bulk_id import BulkId
from app.bulk_persistence.dask.blob_storage import DaskDriverBlobStorage
from app.bulk_persistence.dask.errors import BulkError
from app.clients.storage_service_client import get_storage_record_service
from app.model.model_chunking import GetDataParams
from app.model.model_utils import from_record, to_record
from app.model.osdu_model import WellLog
from app.routers.ddms_v2.log_ddms_v2 import fetch_record  # TODO fetch recod should be moved in common utils
from app.routers.ddms_v3.ddms_v3_utils import DataFrameRender, DMSV3RouterUtils
from app.utils import Context, OpenApiHandler, get_ctx, load_schema_example
from fastapi import (APIRouter, Body, Depends, HTTPException, Request,
                     Response, status)
from odes_storage.models import (CreateUpdateRecordsResponse, List,
                                 RecordVersions)

from ...bulk_persistence import JSONOrient
from ...persistence.sessions_storage import (Session, SessionException,
                                             SessionState, SessionUpdateMode)
from ..common_parameters import (REQUEST_DATA_BODY_SCHEMA, REQUIRED_ROLES_READ,
                                 REQUIRED_ROLES_WRITE, json_orient_parameter)
from ..sessions import (SessionInternal, UpdateSessionState,
                        UpdateSessionStateValue, WithSessionStorages,
                        get_session_dependencies)

router = APIRouter()
router_bulk = APIRouter()  # router dedicated to bulk APIs


@router.get(
    "/welllogs/{welllogid}",
    response_model=WellLog,
    response_model_exclude_unset=True,
    summary="Get the WellLog using osdu schema",
    description="""Get the WellLog object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_welllog_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLog not found"}
    },
)
async def get_welllog_osdu(
        welllogid: str, ctx: Context = Depends(get_ctx)
) -> WellLog:
    storage_client = await get_storage_record_service(ctx)
    welllog_record = await storage_client.get_record(
        id=welllogid, data_partition_id=ctx.partition_id
    )
    return from_record(WellLog, welllog_record)


@router.delete(
    "/welllogs/{welllogid}",
    summary="Delete the welllog. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="del_osdu_welllog",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLog not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_osdu_welllog(welllogid: str, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(
        id=welllogid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/welllogs/{welllogid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellLog",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_welllog_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLog not found"}
    },
)
async def get_osdu_welllog_versions(
        welllogid: str, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=welllogid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/welllogs/{welllogid}/versions/{version}",
    response_model=WellLog,
    summary="Get the given version of the WellLog using OSDU welllog schema",
    description=""""Get the WellLog object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_welllog_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLog not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_welllog_version(
        welllogid: str, version: int, ctx: Context = Depends(get_ctx)
) -> WellLog:
    storage_client = await get_storage_record_service(ctx)
    welllog_record = await storage_client.get_record_version(
        id=welllogid, version=version, data_partition_id=ctx.partition_id
    )
    return from_record(WellLog, welllog_record)


@router.post(
    "/welllogs",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the WellLogs using osdu schema",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="post_welllog_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_welllog_osdu(
        welllogs: List[WellLog] = Body(..., example=load_schema_example("wellLog_v3.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=[to_record(w) for w in welllogs],
        data_partition_id=ctx.partition_id,
    )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ------------- BULK APIs ----------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------

@OpenApiHandler.set(operation_id="post_data", request_body=REQUEST_DATA_BODY_SCHEMA)
@router_bulk.post(
    '/welllogs/{welllog_id}/data',
    summary="Writes data as a whole bulk, creates a new version.",
    description="Writes data to the wellLog | logSet | log (atomic). It creates a new version. "
    "Payload is expected to contain the entire bulk which will replace as latest version "
    "any previous bulk. Previous bulk versions are accessible via the get bulk data version API."
    "Support JSON and Parquet format ('Content_Type' must be set accordingly). "
    "In case of JSON the orient must be set accordingly. Support http chunked encoding.",
    operation_id="write_record_data",
    responses={
        404: {},
        200: {}
    })
async def post_data(welllog_id: str,
                    request: Request,
                    orient: JSONOrient = Depends(json_orient_parameter),
                    ctx: Context = Depends(get_ctx),
                    dask_blob_storage: DaskDriverBlobStorage = Depends(DMSV3RouterUtils.with_dask_blob_storage),
                    ):
    async def save_blob():
        df = await DMSV3RouterUtils.get_df_from_request(request, orient)
        return await dask_blob_storage.save_blob(df)

    record, bulk_id = await asyncio.gather(
        fetch_record(ctx, welllog_id),
        save_blob()
    )
    return await update_record(ctx=ctx, bulk_id=bulk_id, record=record)


@OpenApiHandler.set(operation_id="post_welllog_chunk_data", request_body=REQUEST_DATA_BODY_SCHEMA)
@router_bulk.post(
    "/welllogs/{welllog_id}/sessions/{session_id}/data",
    summary="Send a data chunk. Session must be complete/commit once all chunks are sent.",
    description="Send a data chunk. Session must be complete/commit once all chunks are sent. "
                "This will create a new and single version aggregating all and previous bulk."
                "Support JSON and Parquet format ('Content_Type' must be set accordingly). "
                "In case of JSON the orient must be set accordingly. Support http chunked encoding.",
    operation_id="post_welllog_chunk_data",
    responses={400: {"error": "Record not found"}}
)
async def post_chunk_data(welllog_id: str,
                          session_id: str,
                          request: Request,
                          orient: JSONOrient = Depends(json_orient_parameter),
                          with_session: WithSessionStorages = Depends(get_session_dependencies),
                          dask_blob_storage: DaskDriverBlobStorage = Depends(DMSV3RouterUtils.with_dask_blob_storage),
                          ):
    i_session = await with_session.get_session(welllog_id, session_id)
    if i_session.session.state != SessionState.Open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session cannot accept data, state={i_session.session.state}")

    df = await DMSV3RouterUtils.get_df_from_request(request, orient)
    await dask_blob_storage.session_add_chunk(i_session.session, df)


def get_bulk_uri(record):
    return record.data.get('ExtensionProperties', {}).get('wdms', {}).get('bulkURI', None)


def set_bulk_uri(record, bulk_urn):
    return record.data.update({'ExtensionProperties': {'wdms': {'bulkURI': bulk_urn}}})


async def update_record(ctx: Context, bulk_id, record):
    bulk_urn = BulkId.bulk_urn_encode(bulk_id) # TODO should BulkId be different from v2 and v3
    set_bulk_uri(record, bulk_urn)

    # push new version on the storage
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[record], data_partition_id=ctx.partition_id
    )


@router_bulk.get(
    '/welllogs/{welllog_id}/versions/{version}/data',
    summary='Returns data of the specified version.',
    description='Returns the data of a specific version according to the specified query parameters.'
    ' Multiple media types response are available ("application/json", text/csv", "application/x-parquet")',
    #response_model=RecordData,
    responses={
        404: {},
        200: {"content": {
            "application/json": {},
            "application/x-parquet": {},
            "text/csv": {},
        }}
    }
)
async def get_data_version(
    welllog_id: str, version: int,
    request: Request,
    ctrl_p: GetDataParams = Depends(),
    ctx: Context = Depends(get_ctx),
    dask_blob_storage: DaskDriverBlobStorage = Depends(DMSV3RouterUtils.with_dask_blob_storage),
):
    record = await fetch_record(ctx, welllog_id, version)
    bulk_id = BulkId.bulk_urn_decode(get_bulk_uri(record))
    df = await dask_blob_storage.load_bulk(bulk_id)
    df = await DataFrameRender.process_params(df, ctrl_p)

    return await DataFrameRender.df_render(df, ctrl_p, request.headers.get('Accept'))


@router_bulk.get(
    "/welllogs/{welllog_id}/data",
    summary='Returns the data according to the specified query parameters.',
    description='Returns the data according to the specified query parameters.'
    ' Multiple media types response are available ("application/json", text/csv", "application/x-parquet")',
    #response_model=Union[RecordData, Dict],
    responses={
        404: {},
        200: {"content": {
            "application/json": {},
            "application/x-parquet": {},
            "text/csv": {},
        }}
    }
)
async def get_data(
    welllog_id: str,
    request: Request,
    ctrl_p: GetDataParams = Depends(),
    ctx: Context = Depends(get_ctx),
    dask_blob_storage: DaskDriverBlobStorage = Depends(DMSV3RouterUtils.with_dask_blob_storage),
):
    return await get_data_version(welllog_id, None, request, ctrl_p, ctx, dask_blob_storage)


@router_bulk.patch(
    "/welllogs/{welllog_id}/sessions/{session_id}",
    summary='Update a session, either commit or abandon.',
    response_model=Session
)
async def complete_welllog_session(
    welllog_id: str,
    session_id: str,
    update_request: UpdateSessionState,
    with_session: WithSessionStorages = Depends(get_session_dependencies),
    dask_blob_storage: DaskDriverBlobStorage = Depends(DMSV3RouterUtils.with_dask_blob_storage),
    ctx: Context = Depends(get_ctx),
) -> Session:
    tenant = with_session.tenant
    sessions_storage = with_session.sessions_storage

    try:
        # --------  SESSION COMMIT SEQUENCE -----------------------
        if update_request.state == UpdateSessionStateValue.Commit:
            async with sessions_storage.initiate_commit(tenant, welllog_id, session_id) as commit_guard:
                # get the session if some information is needed
                i_session = commit_guard.session
                internal = i_session.internal  # <=  contains details details, may be irrelevant or not needed

                record = await fetch_record(ctx, welllog_id, i_session.session.fromVersion)
                previous_bulk_uri = None
                bulk_urn = get_bulk_uri(record)
                if i_session.session.mode == SessionUpdateMode.Update and bulk_urn is not None:
                    previous_bulk_uri = BulkId.bulk_urn_decode(bulk_urn)

                new_bulk_uri = await dask_blob_storage.session_commit(i_session.session, previous_bulk_uri)
                # ==============>
                # ==============> UPDATE WELLLOG META DATA HERE (baseDepth, ...) <==============
                # ==============>
                await update_record(ctx, BulkId.bulk_urn_encode(new_bulk_uri), record)

            i_session = commit_guard.session
            i_session.session.meta = i_session.session.meta or {}
            i_session.session.meta.update({"some_detail_about_merge": "like the shape, number of rows ..."})
            return i_session.session

        # --------  SESSION ABANDON SEQUENCE ----------------------
        if update_request.state == UpdateSessionStateValue.Abandon:
            async with sessions_storage.initiate_abandon(tenant, welllog_id, session_id) as abandon_guard:
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
