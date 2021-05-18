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


from fastapi import APIRouter, Depends, Query, status, Response, Body

from app.clients.storage_service_client import get_storage_record_service
from app.clients.search_service_client import get_search_service
from odes_storage.models import *
from app.model.model_curated import logset
from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.utils import Context
from app.utils import get_ctx
from app.utils import load_schema_example
from app.model.model_utils import to_record, from_record
from app.model.entity_utils import Entity

import app.routers.ddms_v2.storage_helper as storage_helper

router = APIRouter()


@router.get('/logsets/{logsetid}',
            response_model=logset,
            summary="Get the LogSet using wks:logSet:1.0.5 schema",
            description="""Get the LogSet object using its **id**. {}""".format(REQUIRED_ROLES_READ),
            operation_id="get_logset",
            responses={status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"}},
            response_model_exclude_unset=True)
async def get_logset(
        logsetid: str,
        ctx: Context = Depends(get_ctx)
) -> logset:
    storage_client = await get_storage_record_service(ctx)
    logset_record = await storage_client.get_record(id=logsetid, data_partition_id=ctx.partition_id)
    return from_record(logset, logset_record)


@router.delete('/logsets/{logsetid}',
               summary="Delete the LogSet. The API performs a logical deletion of the given record",
               description="{}".format(REQUIRED_ROLES_WRITE),
               operation_id="del_logset",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={
                   status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"},
                   status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
               })
async def del_logset(
        logsetid: str,
        recursive: bool = Query(default=False, description="Whether or not to delete records children"),
        ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    if recursive:
        await storage_helper.StorageHelper.delete_recursively(
            ctx,
            entity_id=logsetid,
            relationship='logset',
            entity_list=[Entity.LOG],
            data_partition_id=ctx.partition_id,
            search_service=await get_search_service(ctx),
            storage_service=storage_client
        )
    else:
        await storage_client.delete_record(id=logsetid, data_partition_id=ctx.partition_id)


@router.get('/logsets/{logsetid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the logset.",
            description="{}".format(REQUIRED_ROLES_READ),
            operation_id="get_logset_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"}})
async def get_logset_versions(
        logsetid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=logsetid, data_partition_id=ctx.partition_id)


@router.get('/logsets/{logsetid}/versions/{version}',
            response_model=logset,
            summary="Get the given version of LogSet using wks:logSet:1.0.5 schema",
            description=""""Get the LogSet object using its **id**. {}""".format(REQUIRED_ROLES_READ),
            operation_id="get_logset_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"}},
            response_model_exclude_unset=True)
async def get_logset_version(
        logsetid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> logset:
    storage_client = await get_storage_record_service(ctx)
    result_logset = await storage_client.get_record_version(id=logsetid,
                                                            version=version,
                                                            data_partition_id=ctx.partition_id)
    return from_record(logset, result_logset)

@router.post('/logsets',
             response_model=CreateUpdateRecordsResponse,
             summary="Create or update the LogSets using wks:logSet:1.0.5 schema",
             description="{}".format(REQUIRED_ROLES_WRITE),
             operation_id="post_logset",
             responses={
                 status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def post_logset(
        logsets: List[logset] = Body(..., example= load_schema_example("logSet_v2.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[to_record(lgset) for lgset in logsets],
        data_partition_id=ctx.partition_id)
