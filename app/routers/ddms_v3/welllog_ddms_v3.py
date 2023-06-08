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

from typing import List
from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from starlette.requests import Request

from odes_storage.models import CreateUpdateRecordsResponse, RecordVersions, Record

from app.clients.storage_service_client import get_storage_record_service
from app.consistency import (
    DuplicatedCurveIdException,
    ReferenceCurveIdNotFoundException,
    check_welllog_consistency
)
from app.model.osdu_record_id import split_record_id_version, WellLogId
from app.routers.bulk.bulk_routes_dependencies import BulkIdAccess, get_bulk_id_access
from app.routers.common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.delete.delete_bulk_data import delete_record
from app.routers.record_utils import fetch_record
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.schemas import schema_library
from app.helper.traces import TracingRoute

router = APIRouter(route_class=TracingRoute)

WELL_LOGS_API_BASE_PATH = '/welllogs'


@router.get(
    WELL_LOGS_API_BASE_PATH + "/{welllogid}",
    response_model=Record,
    response_model_exclude_unset=True,
    summary="Get the WellLog using osdu schema",
    description="""Get the WellLog object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_welllog_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLog not found"}
    },
)
async def get_welllog_osdu(
        welllogid: WellLogId, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    # Note: version is dropped here
    welllogid, _ = split_record_id_version(welllogid)

    welllog_record = await storage_client.get_record(
        id=welllogid, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(welllog_record, request.state)
    await schema_library.validate_records([welllog_record], ctx)
    return welllog_record


@router.delete(
    WELL_LOGS_API_BASE_PATH + "/{welllogid}",
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
async def del_osdu_welllog(
    welllogid: WellLogId,
    purge: bool = False,
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
):
    welllogid, _ = split_record_id_version(welllogid)
    await delete_record(record_id=welllogid, purge=purge, ctx=ctx, bulk_uri_access=bulk_uri_access)


@router.get(
    WELL_LOGS_API_BASE_PATH + "/{welllogid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellLog",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_welllog_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLog not found"}
    },
)
async def get_osdu_welllog_versions(
    welllogid: WellLogId, request: Request, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    record = await fetch_record(ctx, welllogid)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    storage_client = await get_storage_record_service(ctx)
    welllogid, _ = split_record_id_version(welllogid)

    return await storage_client.get_all_record_versions(
        id=welllogid, data_partition_id=ctx.partition_id
    )


@router.get(
    WELL_LOGS_API_BASE_PATH + "/{welllogid}/versions/{version}",
    response_model=Record,
    summary="Get the given version of the WellLog using OSDU welllog schema",
    description=""""Get the WellLog object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_welllog_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLog not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_welllog_version(
    welllogid: WellLogId, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    welllogid, _ = split_record_id_version(welllogid)
    welllog_record = await storage_client.get_record_version(
        id=welllogid, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(welllog_record, request.state)
    await schema_library.validate_records([welllog_record], ctx)
    return welllog_record


@router.post(
    WELL_LOGS_API_BASE_PATH,
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
    request: Request,
    welllogs: List[Record] = Body(..., example=load_schema_example("wellLog_v3_120.json")), ctx: Context = Depends(get_ctx),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
) -> CreateUpdateRecordsResponse:
    await schema_library.validate_records(welllogs, ctx)  # Checks the entities Vs their respective schemas
    DMSV3RouterUtils.raise_if_not_osdu_right_entities_kind(welllogs, request.state)  # Checks the kind of the entities is in the list of supported kinds of this API
    # DMSV3RouterUtils.validate_record_against_kinds_schema(welllogs)  # Checks the entities vs their respective schemas ... might be removed
    await DMSV3RouterUtils.raise_if_invalid_bulk_uri(welllogs, bulk_uri_access)
    for idx, w in enumerate(welllogs):
        try:
            check_welllog_consistency(w)
        except DuplicatedCurveIdException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All CurveID in WellLog[{idx}] should be unique"
            )
        except ReferenceCurveIdNotFoundException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"WellLog[{idx}] should have a curve with a curveID value equal to the ReferenceCurveID value:"
                       f" '{w.data.get('ReferenceCurveID', None)}'",
            )

    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=welllogs,
        data_partition_id=ctx.partition_id,
    )
