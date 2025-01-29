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

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
    Body
)
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    RecordVersions,
)

from app.clients.storage_service_client import get_storage_record_service
from app.model.model_curated import log
from app.model.model_utils import from_record, to_record
from app.routers.common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.record_utils import fetch_record, update_records
from app.context import Context, get_ctx
from app.utils import load_schema_example


router = APIRouter()

LOGS_API_BASE_PATH = '/logs'

# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log META -----------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.get('/logs/{logid}',
            response_model=log,
            summary="Get the Log using wks:log:1.0.5 schema",
            description="""Get the log object using its data ecosystem **id**.  <p>If the log
                kind is *wks:log:1.0.5* returns the record directly</p> <p>If the
                wellbore kind is different *wks:log:1.0.5* it will get the raw
                record and convert the results to match the *wks:log:1.0.5*. If
                conversion is not possible returns an error **500**.</p>{}""".format(REQUIRED_ROLES_READ),
            operation_id="get_log",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}},
            response_model_exclude_unset=True)
async def get_log(
        logid: str,
        ctx: Context = Depends(get_ctx)
) -> log:
    record = await fetch_record(ctx, logid)
    return from_record(log, record)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API create or update Log META ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.post('/logs', response_model=CreateUpdateRecordsResponse,
             summary="Create or update the logs using wks:log:1.0.5 schema",
             description="{}".format(REQUIRED_ROLES_WRITE),
             operation_id="post_log",
             responses={
                 status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def post_log(
        logs: List[log] = Body(..., example= load_schema_example("log_v2.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    if len(logs) == 0:
        return CreateUpdateRecordsResponse(recordCount=0, recordIds=[])

    return await update_records(ctx, records=[to_record(lg) for lg in logs])


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------- API delete Log META ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.delete('/logs/{logid}',
               summary="Delete the log. The API performs a logical deletion of the given record",
               description="{}".format(REQUIRED_ROLES_WRITE),
               operation_id="del_log",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          })
async def del_log(
        logid: str,
        ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(id=logid, data_partition_id=ctx.partition_id)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log all versions ---------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.get(
    "/logs/{logid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the log",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_log_versions",
    responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}}
)
async def get_log_versions(
    logid: str, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=logid, data_partition_id=ctx.partition_id
    )


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log @ specific version ---------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------


@router.get(
    "/logs/{logid}/versions/{version}",
    response_model=log,
    summary="Get the given version of log using wks:log:1.0.5 schema",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_log_version",
    responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}},
    response_model_exclude_unset=True
)
async def get_log_version(
    logid: str, version: int, ctx: Context = Depends(get_ctx)
) -> log:
    return from_record(log, await fetch_record(ctx, logid, version))
