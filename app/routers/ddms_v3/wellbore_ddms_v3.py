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

from typing import Listfrom fastapi import APIRouter, Body, Depends, Response, status
from starlette.requests import Request

from odes_storage.models import CreateUpdateRecordsResponse, RecordVersions, Record
from app.model.osdu_record_id import split_record_id_version, WellboreId

from app.clients.storage_service_client import get_storage_record_service
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.record_utils import fetch_record
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.schemas import schema_library

from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE


router = APIRouter()


@router.get(
    "/wellbores/{wellboreid}",
    response_model=Record,
    response_model_exclude_unset=True,
    summary="Get the Wellbore using osdu schema",
    description="""Get the Wellbore object using its **id**.{}""".format(
        REQUIRED_ROLES_READ
    ),
    operation_id="get_wellbore_osdu",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}},
)
async def get_wellbore_osdu(
    wellboreid: WellboreId, ctx: Context = Depends(get_ctx)
) -> Record:
    # Note: version is dropped here
    record_id, _ = split_record_id_version(wellboreid)
    storage_client = await get_storage_record_service(ctx)
    wellbore_record = await storage_client.get_record(
        id=record_id, data_partition_id=ctx.partition_id
    )
    await schema_library.validate_records([wellbore_record], ctx)
    return wellbore_record


@router.delete(
    "/wellbores/{wellboreid}",
    summary="Delete the wellbore. The API performs a logical deletion of the given record. "
    "No recursive delete for OSDU kinds",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="del_osdu_wellbore",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"},
        status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"},
    },
)
async def del_osdu_wellbore(wellboreid: WellboreId, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(
        id=wellboreid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellbores/{wellboreid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the Wellbore",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellbore_versions",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}},
)
async def get_osdu_wellbore_versions(
    wellboreid: WellboreId, request: Request, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    record = await fetch_record(ctx, wellboreid)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=wellboreid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellbores/{wellboreid}/versions/{version}",
    response_model=Record,
    summary="Get the given version of the Wellbore using OSDU wellbore schema",
    description=""""Get the Wellbore object using its **id**. {}""".format(
        REQUIRED_ROLES_READ
    ),
    operation_id="get_osdu_wellbore_version",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}},
    response_model_exclude_unset=True,
)
async def get_osdu_wellbore_version(
    wellboreid: WellboreId,
    version: int,
    request: Request,
    ctx: Context = Depends(get_ctx),
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    wellbore_record = await storage_client.get_record_version(
        id=wellboreid, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellbore_record, request.state)
    await schema_library.validate_records([wellbore_record], ctx)
    return wellbore_record


@router.post(
    "/wellbores",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the Wellbores using osdu schema",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="post_wellbore_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_wellbore_osdu(
    request: Request,
    wellbores: List[Record] = Body(
        ..., example=load_schema_example("wellbore_v3_130.json")
    ),
    ctx: Context = Depends(get_ctx),
) -> CreateUpdateRecordsResponse:
    await schema_library.validate_records(wellbores, ctx)
    DMSV3RouterUtils.raise_if_not_osdu_right_entities_kind(wellbores, request.state)
    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=wellbores,
        data_partition_id=ctx.partition_id,
    )
