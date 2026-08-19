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
from fastapi import APIRouter, Depends, Response, status, Body
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    RecordVersions,
    Record
)
from starlette.requests import Request

from app.clients.storage_service_client import get_storage_record_service
from app.model.osdu_record_id import split_record_id_version, WellboreMarkerSetId
from app.routers.common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.record_utils import fetch_record
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.schemas import schema_library


router = APIRouter()

@router.get(
    "/wellboremarkersets/{record_id}",
    response_model=Record,
    response_model_exclude_unset=True,
    summary="Get the WellboreMarkerSet using osdu schema",
    description=f"""Get the WellboreMarkerSet object using its **id**. {REQUIRED_ROLES_READ}""",
    operation_id="get_wellbore_markerset_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Wellbore Marker Set not found"}
    },
)
async def get_wellbore_markerset_osdu(
        record_id: WellboreMarkerSetId, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    # Note: version is dropped here
    record_id, _ = split_record_id_version(record_id)
    storage_client = await get_storage_record_service(ctx)

    wellboremarkerset_record = await storage_client.get_record(id=record_id, data_partition_id=ctx.partition_id)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellboremarkerset_record, request.state)
    await schema_library.validate_records([wellboremarkerset_record], ctx)
    return wellboremarkerset_record


@router.delete(
    "/wellboremarkersets/{record_id}",
    summary="Delete the wellboreMarkerset. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description=f"{REQUIRED_ROLES_WRITE}",
    operation_id="del_osdu_wellboremarkerset",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreMarkerSet not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_osdu_wellboremarkerset(record_id: WellboreMarkerSetId, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    record_id, _ = split_record_id_version(record_id)
    await storage_client.delete_record(
        id=record_id, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellboremarkersets/{record_id}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellboreMarkerSet",
    description=f"{REQUIRED_ROLES_READ}",
    operation_id="get_osdu_wellboremarkerset_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreMarkerSet not found"}
    },
)
async def get_osdu_wellboremarkerset_versions(
        record_id: WellboreMarkerSetId, request: Request, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    record_id, _ = split_record_id_version(record_id)
    record = await fetch_record(ctx, record_id)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=record_id, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellboremarkersets/{record_id}/versions/{version}",
    response_model=Record,
    summary="Get the given version of the WellboreMarkerSet using OSDU WellboreMarkerset schema",
    description=f""""Get the WellboreMarkerSet object using its **id**. {REQUIRED_ROLES_READ}""",
    operation_id="get_osdu_wellboremarkerset_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreMarkerSet not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_wellboremarkerset_version(
        record_id: WellboreMarkerSetId, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    record_id, _ = split_record_id_version(record_id)

    wellboremarkerset_record = await storage_client.get_record_version(
        id=record_id, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(wellboremarkerset_record, request.state)
    await schema_library.validate_records([wellboremarkerset_record], ctx)
    return wellboremarkerset_record


@router.post(
    "/wellboremarkersets",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the Wellbore Markerset using osdu schema",
    description=f"{REQUIRED_ROLES_WRITE}",
    operation_id="post_wellboremarkerset_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_wellboremarkerset_osdu(
        request: Request,
        wellboremarkersets: List[Record] = Body(..., example= load_schema_example("marker_v3_121.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    await schema_library.validate_records(wellboremarkersets, ctx)
    DMSV3RouterUtils.raise_if_not_osdu_right_entities_kind(wellboremarkersets, request.state)
    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=wellboremarkersets,
        data_partition_id=ctx.partition_id,
    )
