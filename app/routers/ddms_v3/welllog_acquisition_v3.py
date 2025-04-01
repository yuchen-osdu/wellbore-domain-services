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
from app.context import Context, get_ctx
from app.model.osdu_record_id import split_record_id_version, WellLogAcquisitionId
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.record_utils import fetch_record
from app.schemas import schema_library
from app.utils import load_schema_example
from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE

router = APIRouter()


@router.get(
    "/welllogacquisition/{welllogacquisitionid}",
    response_model=Record,
    response_model_exclude_unset=True,
    summary="Get the WellLogAcquisition using osdu schema",
    description=f"Get the WellLogAcquisition object using its **id**. {REQUIRED_ROLES_READ}",
    operation_id="get_welllogacquisitionid_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLogAcquisition not found"}
    },
)
async def get_welllogacquisitionid_osdu(welllogacquisitionid: WellLogAcquisitionId,
                                         ctx: Context = Depends(get_ctx)) -> Record:
    # Note: version is dropped here
    record_id, _ = split_record_id_version(welllogacquisitionid)
    storage_client = await get_storage_record_service(ctx)
    welllogacquisitionid_record = await storage_client.get_record(id=record_id, data_partition_id=ctx.partition_id)
    await schema_library.validate_records([welllogacquisitionid_record], ctx)
    return welllogacquisitionid_record


@router.delete(
    "/welllogacquisition/{welllogacquisitionid}",
    summary="Delete the WellLogAcquisitionId. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description=f"{REQUIRED_ROLES_WRITE}",
    operation_id="del_osdu_welllogacquisitionid",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLogAcquisition not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_osdu_welllogacquisitionid(welllogacquisitionid: WellLogAcquisitionId, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(id=welllogacquisitionid, data_partition_id=ctx.partition_id)


@router.get("/welllogacquisition/{welllogacquisitionid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellLogAcquisition",
    description=f"{REQUIRED_ROLES_READ}",
    operation_id="get_osdu_welllogacquisitionid_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLogAcquisition not found"}
    },
)
async def get_osdu_welllogacquisitionid_versions(welllogacquisitionid: WellLogAcquisitionId, request: Request,
                                                  ctx: Context = Depends(get_ctx)) -> RecordVersions:
    record = await fetch_record(ctx, welllogacquisitionid)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=welllogacquisitionid, data_partition_id=ctx.partition_id)


@router.get("/welllogacquisition/{welllogacquisitionid}/versions/{version}",
    response_model=Record,
    summary="Get the given version of the WellLogAcquisition using OSDU WellLogAcquisitionId schema",
    description=f"Get the WellLogAcquisition object using its **id**. {REQUIRED_ROLES_READ}",
    operation_id="get_osdu_welllogacquisitionid_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellLogAcquisition not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_welllogacquisitionid_version(
        welllogacquisitionid: WellLogAcquisitionId, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    welllogacquisitionid_record = await storage_client.get_record_version(
        id=welllogacquisitionid, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(welllogacquisitionid_record, request.state)
    await schema_library.validate_records([welllogacquisitionid_record], ctx)
    return welllogacquisitionid_record


@router.post("/welllogacquisition",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the WellLogAcquisition using osdu schema",
    description=f"""From WellLog 1.5.0 new attributes are introduced WellLogAcquisitionDetails.WellLogAcquisitionID
    to reference a WellLogAcquisition into a WellLog record. (ref. [WellLog 1.5.0 schemas]
    (https://community.opengroup.org/osdu/data/data-definitions/-/blob/master/Examples/work-product-component/WellLog.1.5.0.json#L405))
    
    {REQUIRED_ROLES_WRITE}
    """,
    operation_id="post_welllogacquisitionid_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_welllogacquisitionid_osdu(
        request: Request,
        welllogacquisitions: List[Record] = Body(..., example=load_schema_example("wellLogacquisition_v3_100.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    await schema_library.validate_records(welllogacquisitions, ctx)
    DMSV3RouterUtils.raise_if_not_osdu_right_entities_kind(welllogacquisitions, request.state)
    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=welllogacquisitions,
        data_partition_id=ctx.partition_id,
    )
