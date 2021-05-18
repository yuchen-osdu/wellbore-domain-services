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


from app.clients.storage_service_client import get_storage_record_service
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    List,
    RecordVersions,
)
from app.model.osdu_model import WellboreTrajectory
from app.routers.common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.utils import Context
from app.utils import get_ctx
from app.utils import load_schema_example
from app.model.model_utils import to_record, from_record


router = APIRouter()


@router.get(
    "/wellboretrajectories/{wellboretrajectoryid}",
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
    wellboretrajectoryid: str, ctx: Context = Depends(get_ctx)
) -> WellboreTrajectory:
    storage_client = await get_storage_record_service(ctx)
    wellboreTrajectory_record = await storage_client.get_record(
        id=wellboretrajectoryid, data_partition_id=ctx.partition_id
    )
    return from_record(WellboreTrajectory, wellboreTrajectory_record)


@router.delete(
    "/wellboretrajectories/{wellboretrajectoryid}",
    summary="Delete the wellboreTrajectory. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="del_osdu_wellboreTrajectory",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_osdu_wellboreTrajectory(wellboretrajectoryid: str, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(
        id=wellboretrajectoryid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellboretrajectories/{wellboretrajectoryid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellboreTrajectory",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellboreTrajectory_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreTrajectory not found"}
    },
)
async def get_osdu_wellboreTrajectory_versions(
    wellboretrajectoryid: str, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=wellboretrajectoryid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellboretrajectories/{wellboretrajectoryid}/versions/{version}",
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
    wellboretrajectoryid: str, version: int, ctx: Context = Depends(get_ctx)
) -> WellboreTrajectory:
    storage_client = await get_storage_record_service(ctx)
    wellboreTrajectory_record = await storage_client.get_record_version(
        id=wellboretrajectoryid, version=version, data_partition_id=ctx.partition_id
    )
    return from_record(WellboreTrajectory, wellboreTrajectory_record)


@router.post(
    "/wellboretrajectories",
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
    wellboretrajectories: List[WellboreTrajectory], ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:

    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=[to_record(w) for w in wellboretrajectories],
        data_partition_id=ctx.partition_id,
    )
