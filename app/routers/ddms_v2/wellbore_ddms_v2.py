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
from app.model.model_curated import *
from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.model.model_utils import to_record, from_record
from app.model.entity_utils import Entity

import app.routers.ddms_v2.storage_helper as storage_helper


router = APIRouter()


@router.get('/wellbores/{wellboreid}', response_model=wellbore,
            summary="Get the Wellbore using wks:wellbore:1.0.6 schema",
            description="""Get the Wellbore object using its **id**.  <p>If the wellbore kind is
        *wks:wellbore:1.0.6* returns the record directly</p> <p>If the wellbore
        kind is different *wks:wellbore:1.0.6* it will get the raw record and
        convert the results to match the *wks:wellbore:1.0.6*. If convertion is
        not possible returns an error **500**. {}""".format(REQUIRED_ROLES_READ),
            operation_id="get_wellbore",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}},
            response_model_exclude_unset=True)
async def get_wellbore(
        wellboreid: str,
        ctx: Context = Depends(get_ctx)
) -> wellbore:
    storage_client = await get_storage_record_service(ctx)
    wellbore_record = await storage_client.get_record(id=wellboreid, data_partition_id=ctx.partition_id)
    return from_record(wellbore, wellbore_record)


@router.delete('/wellbores/{wellboreid}',
               summary="Delete the wellbore. The API performs a logical deletion of the given record",
               description="{}".format(REQUIRED_ROLES_WRITE),
               operation_id="del_wellbore",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          }
               )
async def del_wellbore(
        wellboreid: str,
        recursive: bool = Query(default=False, description="Whether or not to delete records children"),
        ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    if recursive:
        await storage_helper.StorageHelper.delete_recursively(
            ctx,
            entity_id=wellboreid,
            relationship='wellbore',
            entity_list=[Entity.LOGSET, Entity.LOG, Entity.MARKER],
            data_partition_id=ctx.partition_id,
            search_service=await get_search_service(ctx),
            storage_service=storage_client
        )
    else:
        await storage_client.delete_record(id=wellboreid, data_partition_id=ctx.partition_id)


@router.get('/wellbores/{wellboreid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the Wellbore",
            description="{}".format(REQUIRED_ROLES_READ),
            operation_id="get_wellbore_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}})
async def get_wellbore_versions(
        wellboreid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=wellboreid, data_partition_id=ctx.partition_id)


@router.get('/wellbores/{wellboreid}/versions/{version}',
            response_model=wellbore,
            summary="Get the given version of the Wellbore using wks:wellbore:1.0.6 schema",
            description=""""Get the Wellbore object using its **id**.  <p>If the wellbore kind is
        *wks:wellbore:1.0.6* returns the record directly</p> <p>If the wellbore
        kind is different *wks:wellbore:1.0.6* it will get the raw record and
        convert the results to match the *wks:wellbore:1.0.6*. If convertion is
        not possible returns an error **500**. {}""".format(REQUIRED_ROLES_READ),
            operation_id="get_wellbore_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}},
            response_model_exclude_unset=True)
async def get_wellbore_version(
        wellboreid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> wellbore:
    storage_client = await get_storage_record_service(ctx)
    wellbore_record = await storage_client.get_record_version(id=wellboreid,
                                                              version=version,
                                                              data_partition_id=ctx.partition_id)
    return from_record(wellbore, wellbore_record)

@router.post('/wellbores',
             response_model=CreateUpdateRecordsResponse,
             summary="Create or update the Wellbores using wks:wellbore:1.0.6 schema",
             description="{}".format(REQUIRED_ROLES_WRITE),
             operation_id="post_wellbore",
             responses={
                 status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def post_wellbore(
        wellbores: List[wellbore] = Body(..., example=load_schema_example("wellbore_v2.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[to_record(w) for w in wellbores],
        data_partition_id=ctx.partition_id)
