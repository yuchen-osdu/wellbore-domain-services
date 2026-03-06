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
from app.consistency import DuplicatedStationProperties, check_trajectory_consistency
from app.model.osdu_record_id import split_record_id_version, WellboreTrajectoryId
from app.routers.bulk.bulk_routes_dependencies import BulkIdAccess, get_bulk_id_access
from app.routers.common_parameters import BULK_URI_RULES, REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.delete.delete_bulk_data import delete_record
from app.routers.record_utils import fetch_record
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.schemas import schema_library


router = APIRouter()

WELLBORE_TRAJECTORIES_API_BASE_PATH = '/wellboretrajectories'


@router.get(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}",
    response_model=Record,
    response_model_exclude_unset=True,
    summary="Get the WellboreTrajectory using osdu schema",
    description=f"""Get the WellboreTrajectory object using its **id**. {REQUIRED_ROLES_READ}""",
    operation_id="get_wellbore_trajectory_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Wellbore Trajectory not found"}
    },
)
async def get_wellbore_trajectory_osdu(
    wellboretrajectoryid: WellboreTrajectoryId, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    # Note: version is dropped here
    wellboretrajectoryid, _ = split_record_id_version(wellboretrajectoryid)

    wellboretrajectory_record = await storage_client.get_record(
        id=wellboretrajectoryid, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellboretrajectory_record, request.state)
    await schema_library.validate_records([wellboretrajectory_record], ctx)
    return wellboretrajectory_record


@router.delete(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}",
    summary="Delete the wellboreTrajectory. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description=f"{REQUIRED_ROLES_WRITE}",
    operation_id="del_osdu_wellboretrajectory",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"},
        status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"},
    },
)
async def del_osdu_wellboretrajectory(
    wellboretrajectoryid: WellboreTrajectoryId,
    purge: bool = False,
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
):
    wellboretrajectoryid, _ = split_record_id_version(wellboretrajectoryid)
    await delete_record(record_id=wellboretrajectoryid, purge=purge, ctx=ctx, bulk_uri_access=bulk_uri_access)


@router.get(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellboreTrajectory",
    description=f"{REQUIRED_ROLES_READ}",
    operation_id="get_osdu_wellboretrajectory_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"}
    },
)
async def get_osdu_wellboretrajectory_versions(
    wellboretrajectoryid: WellboreTrajectoryId, request: Request, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    record = await fetch_record(ctx, wellboretrajectoryid)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    wellboretrajectoryid, _ = split_record_id_version(wellboretrajectoryid)

    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=wellboretrajectoryid, data_partition_id=ctx.partition_id
    )


@router.get(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}/versions/{version}",
    response_model=Record,
    summary="Get the given version of the WellboreTrajectory using OSDU wellboreTrajectory schema",
    description=f""""Get the WellboreTrajectory object using its **id**. {REQUIRED_ROLES_READ}""",
    operation_id="get_osdu_wellboretrajectory_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_wellboretrajectory_version(
    wellboretrajectoryid: WellboreTrajectoryId, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    wellboretrajectoryid, _ = split_record_id_version(wellboretrajectoryid)
    wellboretrajectory_record = await storage_client.get_record_version(
        id=wellboretrajectoryid, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellboretrajectory_record, request.state)
    await schema_library.validate_records([wellboretrajectory_record], ctx)
    return wellboretrajectory_record


@router.post(
    WELLBORE_TRAJECTORIES_API_BASE_PATH,
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the WellboreTrajectories using osdu schema",
    description=f"{REQUIRED_ROLES_WRITE}{BULK_URI_RULES}",
    operation_id="post_wellboretrajectory_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_wellboretrajectory_osdu(
    request: Request,
    wellboretrajectories: List[Record] = Body(..., example=load_schema_example("trajectory_v3.json")),
    ctx: Context = Depends(get_ctx), bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
) -> CreateUpdateRecordsResponse:
    await schema_library.validate_records(wellboretrajectories, ctx)
    DMSV3RouterUtils.raise_if_not_osdu_right_entities_kind(wellboretrajectories, request.state)
    await DMSV3RouterUtils.raise_if_invalid_bulk_uri(wellboretrajectories, bulk_uri_access)
    for idx, traj in enumerate(wellboretrajectories):
        try:
            check_trajectory_consistency(traj)
        except DuplicatedStationProperties:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All station properties in WellboreTrajectory[{idx}] should be unique",
            )

    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=wellboretrajectories,
        data_partition_id=ctx.partition_id,
    )
