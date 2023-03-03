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

from fastapi import APIRouter, Depends, Response, status, Body
from starlette.requests import Request

from app.clients.storage_service_client import get_storage_record_service
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    List,
    RecordVersions,
)
from app.model.osdu_model import WellboreIntervalSet100 as WellboreIntervalSet
from app.model.osdu_record_id import split_record_id_version, WellboreIntervalSetId
from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.model.model_utils import to_record, from_record
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.record_utils import fetch_record
from app.helper.traces import TracingRoute

router = APIRouter(route_class=TracingRoute)


@router.get(
    "/wellboreintervalsets/{wellboreintervalsetsid}",
    response_model=WellboreIntervalSet,
    response_model_exclude_unset=True,
    summary="Get the WellboreIntervalSet using osdu schema",
    description="""Get the WellboreIntervalSet object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_wellboreintervalsetid_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreIntervalSet not found"}
    },
)
async def get_wellboreintervalsetid_osdu(wellboreintervalsetsid: WellboreIntervalSetId,
                                         ctx: Context = Depends(get_ctx)) -> WellboreIntervalSet:
    # Note: version is dropped here
    record_id, _ = split_record_id_version(wellboreintervalsetsid)
    storage_client = await get_storage_record_service(ctx)
    wellboreintervalsetid_record = await storage_client.get_record(id=record_id, data_partition_id=ctx.partition_id)
    return from_record(WellboreIntervalSet, wellboreintervalsetid_record)


@router.delete(
    "/wellboreintervalsets/{wellboreintervalsetsid}",
    summary="Delete the WellboreIntervalSetId. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="del_osdu_wellboreintervalsetid",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreIntervalSet not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_osdu_wellboreintervalsetid(wellboreintervalsetsid: WellboreIntervalSetId, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(id=wellboreintervalsetsid, data_partition_id=ctx.partition_id)


@router.get(
    "/wellboreintervalsets/{wellboreintervalsetsid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellboreIntervalSet",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellboreintervalsetid_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreIntervalSet not found"}
    },
)
async def get_osdu_wellboreintervalsetid_versions(wellboreintervalsetsid: WellboreIntervalSetId, request: Request,
                                                  ctx: Context = Depends(get_ctx)) -> RecordVersions:
    record = await fetch_record(ctx, wellboreintervalsetsid)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=wellboreintervalsetsid, data_partition_id=ctx.partition_id)


@router.get(
    "/wellboreintervalsets/{wellboreintervalsetsid}/versions/{version}",
    response_model=WellboreIntervalSet,
    summary="Get the given version of the WellboreIntervalSet using OSDU WellboreIntervalSetId schema",
    description="""Get the WellboreIntervalSet object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellboreintervalsetid_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreIntervalSet not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_wellboreintervalsetid_version(
        wellboreintervalsetsid: WellboreIntervalSetId, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> WellboreIntervalSet:
    storage_client = await get_storage_record_service(ctx)
    wellboreintervalsetid_record = await storage_client.get_record_version(
        id=wellboreintervalsetsid, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellboreintervalsetid_record, request.state)
    return from_record(WellboreIntervalSet, wellboreintervalsetid_record)


@router.post(
    "/wellboreintervalsets",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the Wells using osdu schema",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="post_wellboreintervalsetid_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_wellboreintervalsetid_osdu(
        wells: List[WellboreIntervalSet] = Body(..., example=load_schema_example("wellboreintervalset_v3_100.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    DMSV3RouterUtils.validate_record_against_kinds_schema(wells)
    storage_client = await get_storage_record_service(ctx)

    r = await storage_client.create_or_update_records(
        record=[to_record(w) for w in wells],
        data_partition_id=ctx.partition_id,
    )
    return r
