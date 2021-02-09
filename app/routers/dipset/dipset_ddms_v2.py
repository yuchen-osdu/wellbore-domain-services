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

import starlette.status as status
from fastapi import APIRouter, Depends, Query
from odes_storage.models import *
from starlette.responses import Response

import app.routers.ddms_v2.storage_helper as storage_helper
from app.clients.search_service_client import get_search_service
from app.clients.storage_service_client import get_storage_record_service
from app.model.model_curated import dipset
from app.model.model_utils import from_record, to_record
from app.model.entity_utils import Entity
from app.utils import Context, get_ctx

router = APIRouter()
@router.post(
    "/dipsets",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the DipSets using wks:dipSet:1.0.0 schema",
    operation_id="post_dipset",
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}},
)
async def post_dipset(dipsets: List[dipset], ctx: Context = Depends(get_ctx)) -> CreateUpdateRecordsResponse:
    # TODO disallow  creation of a dipset without wellbore

    storage_client = await get_storage_record_service(ctx)
    record = await storage_client.create_or_update_records(
        record=[to_record(dipset) for dipset in dipsets], data_partition_id=ctx.partition_id
    )
    return record


@router.get(
    "/dipsets/{dipsetid}/versions/{version}",
    response_model=dipset,
    summary="Get the given version of DipSet using wks:dipset:1.0.0 schema",
    description=""""Get the DipSet object using its **id**.""",
    operation_id="get_dipset_version",
    responses={status.HTTP_404_NOT_FOUND: {"description": "DipSet not found"}},
)
async def get_dipset_version(dipsetid: str, version: int, ctx: Context = Depends(get_ctx)) -> dipset:
    storage_client = await get_storage_record_service(ctx)
    result = await storage_client.get_record_version(id=dipsetid, version=version,
                                                     data_partition_id=ctx.partition_id)
    return from_record(dipset, result)


@router.get(
    "/dipsets/{dipsetid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the dipset",
    operation_id="get_dipset_versions",
    responses={status.HTTP_404_NOT_FOUND: {"description": "DipSet not found"}},
)
async def get_dipset_versions(dipsetid: str, ctx: Context = Depends(get_ctx)) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=dipsetid, data_partition_id=ctx.partition_id)


@router.get(
    "/dipsets/{dipsetid}",
    response_model=dipset,
    summary="Get the DipSet using wks:dipSet:1.0.0 schema",
    description="""Get the DipSet object using its **id**""",
    operation_id="get_dipset",
    responses={status.HTTP_404_NOT_FOUND: {"description": "DipSet not found"}},
)
async def get_dipset(dipsetid: str, ctx: Context = Depends(get_ctx)) -> dipset:
    storage_client = await get_storage_record_service(ctx)
    record = await storage_client.get_record(id=dipsetid, data_partition_id=ctx.partition_id)
    return from_record(dipset, record)


@router.delete(
    "/dipsets/{dipsetid}",
    summary="Delete the DipSet. The API performs a logical deletion of the given record",
    operation_id="del_dipset",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "DipSet not found"},
        status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"},
    },
)
async def del_dipset(dipsetid: str,
                     recursive: bool = Query(default=False, description="Whether or not to delete records children"),
                     ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    if recursive:
        await storage_helper.StorageHelper.delete_recursively(
            ctx,
            entity_id=dipsetid,
            relationship="dipset",
            entity_list=[Entity.LOG],
            data_partition_id=ctx.partition_id,
            search_service=await get_search_service(ctx),
            storage_service=storage_client,
        )
    else:
        await storage_client.delete_record(id=dipsetid, data_partition_id=ctx.partition_id)
