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

from fastapi import APIRouter, status, Depends, Body, Response, HTTPException
from odes_storage.models import (
    Record, RecordVersions, CreateUpdateRecordsResponse
)
from starlette.requests import Request

from app.clients.storage_service_client import get_storage_record_service
from app.context import Context, get_ctx
from app.model.osdu_record_id import PPFGDatasetId, split_record_id_version
from app.routers.bulk.bulk_routes_dependencies import BulkIdAccess, get_bulk_id_access
from app.routers.common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.record_utils import fetch_record
from app.schemas import schema_library
from app.utils import load_schema_example
from app.consistency.ppfgdataset_consistency import (
    DuplicatedCurveIdException,
    PrimaryReferenceCurveIdNotFoundException,
    ContextTypeIdMissingException,
    ReferenceWellTrajectoryIdMissingException,
    check_ppfgdataset_consistency
)

router = APIRouter()
PPFGDATASET_API_BASE_PATH='/ppfgdataset'

@router.get(
    PPFGDATASET_API_BASE_PATH + "/{ppfgdatasetid}",
    response_model=Record,
    response_model_exclude_unset=True,
    summary="Get the PPFGDataset using osdu schema",
    description=REQUIRED_ROLES_READ,
    operation_id="get_ppfgdataset_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "PPFGDataset not found"}
    },
)
async def get_ppfgdataset_osdu(ppfgdatasetid: PPFGDatasetId, request : Request,
                                 ctx: Context = Depends(get_ctx)) -> Record:
    # Note: version is dropped here
    record_id, _ = split_record_id_version(ppfgdatasetid)
    storage_client = await get_storage_record_service(ctx)
    ppfgdataset_record = await storage_client.get_record(id=record_id, data_partition_id=ctx.partition_id)

    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(ppfgdataset_record, request.state)
    await schema_library.validate_records([ppfgdataset_record], ctx)
    return ppfgdataset_record


@router.delete(
    PPFGDATASET_API_BASE_PATH + "/{ppfgdatasetid}",
    summary="Delete the PPFGDataset using id. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description=REQUIRED_ROLES_WRITE,
    operation_id="del_osdu_ppfgdataset",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "PPFGDataset not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_osdu_ppfgdataset(ppfgdatasetid: PPFGDatasetId, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(id=ppfgdatasetid, data_partition_id=ctx.partition_id)


@router.get(PPFGDATASET_API_BASE_PATH + "/{ppfgdatasetid}/versions",
            response_model=RecordVersions,
            summary="Get all versions of PPFGDataset",
            description=REQUIRED_ROLES_READ,
            operation_id="get_osdu_ppfgdataset_versions",
            responses={
                status.HTTP_404_NOT_FOUND: {"description": "PPFGDataset not found"}
            },
            )
async def get_osdu_ppfgdataset_versions(ppfgdatasetid: PPFGDatasetId, request: Request,
                                          ctx: Context = Depends(get_ctx)) -> RecordVersions:
    record = await fetch_record(ctx, ppfgdatasetid)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=ppfgdatasetid, data_partition_id=ctx.partition_id)


@router.get(PPFGDATASET_API_BASE_PATH + "/{ppfgdatasetid}/versions/{version}",
            response_model=Record,
            summary="Get the given version of PPFGDataset using OSDU PPFGDataset schema",
            description="Get the specific version of PPFGDataset object using its **id**. " + REQUIRED_ROLES_READ,
            operation_id="get_osdu_ppfgdataset_version",
            responses={
                status.HTTP_404_NOT_FOUND: {"description": "PPFGDataset not found"}
            },
            response_model_exclude_unset=True,
            )
async def get_osdu_ppfgdataset_version(
        ppfgdatasetid: PPFGDatasetId, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    ppfgdataset_record = await storage_client.get_record_version(
        id=ppfgdatasetid, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(ppfgdataset_record, request.state)
    await schema_library.validate_records([ppfgdataset_record], ctx)
    return ppfgdataset_record


@router.post(PPFGDATASET_API_BASE_PATH,
             response_model=CreateUpdateRecordsResponse,
             summary="Create or update the PPFGDataset using osdu schema",
             description=REQUIRED_ROLES_WRITE,
             operation_id="post_ppfgdataset_osdu",
             responses={
                 status.HTTP_400_BAD_REQUEST: {
                     "description": "Missing mandatory parameter or unknown parameter"
                 }
             },
             )
async def post_ppfgdataset_osdu(
        request: Request,
        ppfgdatasets: List[Record] = Body(..., example=load_schema_example("ppfgdataset_v3_120.json")), ctx: Context = Depends(get_ctx),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
) -> CreateUpdateRecordsResponse:
    await schema_library.validate_records(ppfgdatasets, ctx)
    DMSV3RouterUtils.raise_if_not_osdu_right_entities_kind(ppfgdatasets, request.state)

    #Checking if the update is accidentally overriding the bulk data connection with this record.
    await DMSV3RouterUtils.raise_if_invalid_bulk_uri(ppfgdatasets, bulk_uri_access)

    for ppfgdataset in ppfgdatasets:
        try:
            check_ppfgdataset_consistency(ppfgdataset)
        except DuplicatedCurveIdException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All CurveIDs in the dataset must be unique."
            )
        except PrimaryReferenceCurveIdNotFoundException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No curve with a curveID value equal to the PrimaryReferenceCurveId was found."
            )
        except ContextTypeIdMissingException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The ContextTypeId field is missing in the dataset."
            )
        except ReferenceWellTrajectoryIdMissingException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The ReferenceWellTrajectoryID field is missing in the dataset."
            )

    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=ppfgdatasets,
        data_partition_id=ctx.partition_id,
    )
