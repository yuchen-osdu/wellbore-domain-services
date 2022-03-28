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

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from odes_storage.models import CreateUpdateRecordsResponse, List, RecordVersions
from starlette.requests import Request

from app.clients.storage_service_client import get_storage_record_service
from app.consistency import DuplicatedStationProperties, check_trajectory_consistency
from app.model.model_utils import from_record, to_record
from app.model.osdu_model import WellboreTrajectory110 as WellboreTrajectory
from app.routers.bulk.bulk_uri_dependencies import BulkIdAccess, get_bulk_id_access
from app.routers.common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.ddms_v3.ddms_v3_utils import OSDU_WELLBORETRAJECTORY_VERSION_REGEX, DMSV3RouterUtils
from app.routers.delete.delete_bulk_data import delete_record
from app.routers.record_utils import fetch_record
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.helper.traces import TracingRoute

router = APIRouter(route_class=TracingRoute)

WELLBORE_TRAJECTORIES_API_BASE_PATH = '/wellboretrajectories'


@router.get(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}",
    response_model=WellboreTrajectory,
    response_model_exclude_unset=True,
    summary="Get the WellboreTrajectory using osdu schema",
    description="""Get the WellboreTrajectory object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_wellbore_trajectory_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Wellbore Trajectory not found"}
    },
)
async def get_wellbore_trajectory_osdu(
    wellboretrajectoryid: str, request: Request, ctx: Context = Depends(get_ctx)
) -> WellboreTrajectory:
    storage_client = await get_storage_record_service(ctx)
    wellboretrajectoryid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLBORETRAJECTORY_VERSION_REGEX,
                                                                  wellboretrajectoryid)

    wellboreTrajectory_record = await storage_client.get_record(
        id=wellboretrajectoryid, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellboreTrajectory_record, request.state)
    return from_record(WellboreTrajectory, wellboreTrajectory_record)


@router.delete(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}",
    summary="Delete the wellboreTrajectory. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="del_osdu_wellboreTrajectory",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"},
        status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"},
    },
)
async def del_osdu_wellboreTrajectory(
    wellboretrajectoryid: str,
    purge: bool = False,
    ctx: Context = Depends(get_ctx),
    bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
):
    wellboretrajectoryid = DMSV3RouterUtils.get_id_without_version(
        OSDU_WELLBORETRAJECTORY_VERSION_REGEX, wellboretrajectoryid
    )
    await delete_record(record_id=wellboretrajectoryid, purge=purge, ctx=ctx, bulk_uri_access=bulk_uri_access)


@router.get(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellboreTrajectory",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellboreTrajectory_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"}
    },
)
async def get_osdu_wellboreTrajectory_versions(
    wellboretrajectoryid: str, request: Request, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    record = await fetch_record(ctx, wellboretrajectoryid)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    wellboretrajectoryid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLBORETRAJECTORY_VERSION_REGEX,
                                                                  wellboretrajectoryid)
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=wellboretrajectoryid, data_partition_id=ctx.partition_id
    )


@router.get(
    WELLBORE_TRAJECTORIES_API_BASE_PATH + "/{wellboretrajectoryid}/versions/{version}",
    response_model=WellboreTrajectory,
    summary="Get the given version of the WellboreTrajectory using OSDU wellboreTrajectory schema",
    description=""""Get the WellboreTrajectory object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellboreTrajectory_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_wellboreTrajectory_version(
    wellboretrajectoryid: str, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> WellboreTrajectory:
    storage_client = await get_storage_record_service(ctx)
    wellboretrajectoryid = DMSV3RouterUtils.get_id_without_version(
        OSDU_WELLBORETRAJECTORY_VERSION_REGEX, wellboretrajectoryid
    )
    wellboreTrajectory_record = await storage_client.get_record_version(
        id=wellboretrajectoryid, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellboreTrajectory_record, request.state)
    return from_record(WellboreTrajectory, wellboreTrajectory_record)


@router.post(
    WELLBORE_TRAJECTORIES_API_BASE_PATH,
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the WellboreTrajectories using osdu schema",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="post_wellboreTrajectory_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_wellboreTrajectory_osdu(
    wellboretrajectories: List[WellboreTrajectory] = Body(..., example=load_schema_example("trajectory_v3.json")),
    ctx: Context = Depends(get_ctx), bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
) -> CreateUpdateRecordsResponse:
    DMSV3RouterUtils.validate_record_against_kinds_schema(wellboretrajectories)
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
        record=[to_record(w) for w in wellboretrajectories],
        data_partition_id=ctx.partition_id,
    )
