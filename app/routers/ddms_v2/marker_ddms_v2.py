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
from fastapi import APIRouter, Depends, Query, Response, status, Body

from app.clients.storage_service_client import get_storage_record_service
from odes_storage.models import *
from app.model.model_curated import *
from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.context import Context, get_ctx
from app.utils import load_schema_example
from app.model.model_utils import to_record, from_record


router = APIRouter()


@router.get('/markers/{markerid}',
            response_model=marker,
            summary="Get the marker using wks:marker:1.0.4 schema",
            description="""Get the Marker object using its **id**. {}""".format(REQUIRED_ROLES_READ),
            operation_id="get_marker",
            responses={status.HTTP_404_NOT_FOUND: {"description": "marker not found"}},
            response_model_exclude_unset=True)
async def get_marker(
        markerid: str,
        ctx: Context = Depends(get_ctx)
) -> marker:
    storage_client = await get_storage_record_service(ctx)
    marker_record = await storage_client.get_record(id=markerid, data_partition_id=ctx.partition_id)
    return from_record(marker, marker_record)


@router.delete('/markers/{markerid}',
               summary="Delete the marker. The API performs a logical deletion of the given record",
               description="{}".format(REQUIRED_ROLES_WRITE),
               operation_id="del_marker",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "Marker not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          }
               )
async def del_marker(
        markerid: str,
        ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(id=markerid, data_partition_id=ctx.partition_id)


@router.get('/markers/{markerid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the marker",
            description="{}".format(REQUIRED_ROLES_READ),
            operation_id="get_marker_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "marker not found"}})
async def get_marker_versions(
        markerid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=markerid, data_partition_id=ctx.partition_id)


@router.get('/markers/{markerid}/versions/{version}',
            response_model=marker,
            summary="Get the given version of marker using wks:marker:1.0.4 schema",
            description="{}".format(REQUIRED_ROLES_READ),
            operation_id="get_marker_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "marker not found"}},
            response_model_exclude_unset=True)
async def get_marker_version(
        markerid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> marker:
    storage_client = await get_storage_record_service(ctx)
    result_marker = await storage_client.get_record_version(id=markerid,
                                                            version=version,
                                                            data_partition_id=ctx.partition_id)
    return from_record(marker, result_marker)


@router.post('/markers', response_model=CreateUpdateRecordsResponse,
             summary="Create or update the markers using wks:marker:1.0.4 schema",
             description="{}".format(REQUIRED_ROLES_WRITE),
             operation_id="post_marker",
             responses={
                 status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def post_marker(
        markers: List[marker] = Body(..., example = load_schema_example("marker_v2.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[to_record(mk) for mk in markers],
        data_partition_id=ctx.partition_id)
