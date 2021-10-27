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

from fastapi import (
    APIRouter,
    Body, Depends,
    Response,
    status)


from odes_storage.models import (CreateUpdateRecordsResponse, List,
                                 RecordVersions)
from starlette.requests import Request

from app.clients.storage_service_client import get_storage_record_service
from app.model.model_utils import from_record, to_record
from app.model.osdu_model import WellLog110 as WellLog

from app.utils import Context, get_ctx, load_schema_example
from .ddms_v3_utils import DMSV3RouterUtils, OSDU_WELLLOG_VERSION_REGEX

from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from ..record_utils import fetch_record

router = APIRouter()

WELL_LOGS_API_BASE_PATH = '/welllogs'


@router.get(
    WELL_LOGS_API_BASE_PATH + "/{welllogid}",
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
        welllogid: str, request: Request, ctx: Context = Depends(get_ctx)
) -> WellLog:
    storage_client = await get_storage_record_service(ctx)
    welllogid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLLOG_VERSION_REGEX,
                                                                  welllogid)
    welllog_record = await storage_client.get_record(
        id=welllogid, data_partition_id=ctx.partition_id
    )
    await DMSV3RouterUtils.is_osdu_right_entity_id(welllog_record, request)
    return from_record(WellLog, welllog_record)


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
async def del_osdu_welllog(welllogid: str, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    welllogid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLLOG_VERSION_REGEX,
                                                                  welllogid)
    await storage_client.delete_record(
        id=welllogid, data_partition_id=ctx.partition_id
    )


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
        welllogid: str, request: Request, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    record = await fetch_record(ctx, welllogid)
    await DMSV3RouterUtils.is_osdu_right_entity_id(record, request)
    storage_client = await get_storage_record_service(ctx)
    welllogid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLLOG_VERSION_REGEX,
                                                                  welllogid)
    return await storage_client.get_all_record_versions(
        id=welllogid, data_partition_id=ctx.partition_id
    )


@router.get(
    WELL_LOGS_API_BASE_PATH + "/{welllogid}/versions/{version}",
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
        welllogid: str, version: int, request: Request, ctx: Context = Depends(get_ctx)
) -> WellLog:
    storage_client = await get_storage_record_service(ctx)
    welllogid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLLOG_VERSION_REGEX,
                                                                  welllogid)
    welllog_record = await storage_client.get_record_version(
        id=welllogid, version=version, data_partition_id=ctx.partition_id
    )
    await DMSV3RouterUtils.is_osdu_right_entity_id(welllog_record, request)
    return from_record(WellLog, welllog_record)


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
        welllogs: List[WellLog] = Body(..., example=load_schema_example("wellLog_v3.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=[to_record(w) for w in welllogs],
        data_partition_id=ctx.partition_id,
    )
