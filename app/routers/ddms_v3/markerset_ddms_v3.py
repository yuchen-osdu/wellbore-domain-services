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

from fastapi import APIRouter, Depends, Response, status, Body
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    List,
    RecordVersions,
)

from app.clients.storage_service_client import get_storage_record_service
from app.model.model_utils import to_record, from_record
from app.model.osdu_model import WellboreMarkerSet
from app.routers.common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils, OSDU_WELLBOREMARKERSET_VERSION_REGEX
from app.utils import Context
from app.utils import get_ctx
from app.utils import load_schema_example

router = APIRouter()

@router.get(
    "/wellboremarkersets/{wellboremarkersetid}",
    response_model=WellboreMarkerSet,
    response_model_exclude_unset=True,
    summary="Get the WellboreMarkerSet using osdu schema",
    description="""Get the WellboreMarkerSet object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_wellbore_markerset_osdu",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Wellbore Marker Set not found"}
    },
)
async def get_wellbore_markerset_osdu(
        wellboremarkersetid: str, ctx: Context = Depends(get_ctx)
) -> WellboreMarkerSet:
    storage_client = await get_storage_record_service(ctx)
    wellboremarkersetid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLBOREMARKERSET_VERSION_REGEX,
                                                                  wellboremarkersetid)
    wellboreMarkerset_record = await storage_client.get_record(
        id=wellboremarkersetid, data_partition_id=ctx.partition_id
    )
    return from_record(WellboreMarkerSet, wellboreMarkerset_record)


@router.delete(
    "/wellboremarkersets/{wellboremarkersetid}",
    summary="Delete the wellboreMarkerset. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="del_osdu_wellboreMarkerset",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreMarkerSet not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_osdu_wellboreMarkerset(wellboremarkersetid: str, ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    wellboremarkersetid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLBOREMARKERSET_VERSION_REGEX,
                                                                  wellboremarkersetid)
    await storage_client.delete_record(
        id=wellboremarkersetid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellboremarkersets/{wellboremarkersetid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the WellboreMarkerSet",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellboreMarkerset_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreMarkerSet not found"}
    },
)
async def get_osdu_wellboreMarkerset_versions(
        wellboremarkersetid: str, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=wellboremarkersetid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/wellboremarkersets/{wellboremarkersetid}/versions/{version}",
    response_model=WellboreMarkerSet,
    summary="Get the given version of the WellboreMarkerSet using OSDU WellboreMarkerset schema",
    description=""""Get the WellboreMarkerSet object using its **id**. {}""".format(REQUIRED_ROLES_READ),
    operation_id="get_osdu_wellboreMarkerset_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "WellboreMarkerSet not found"}
    },
    response_model_exclude_unset=True,
)
async def get_osdu_wellboreMarkerset_version(
        wellboremarkersetid: str, version: int, ctx: Context = Depends(get_ctx)
) -> WellboreMarkerSet:
    storage_client = await get_storage_record_service(ctx)
    wellboremarkersetid = DMSV3RouterUtils.get_id_without_version(OSDU_WELLBOREMARKERSET_VERSION_REGEX,
                                                                  wellboremarkersetid)
    wellboreMarkerset_record = await storage_client.get_record_version(
        id=wellboremarkersetid, version=version, data_partition_id=ctx.partition_id
    )
    return from_record(WellboreMarkerSet, wellboreMarkerset_record)


@router.post(
    "/wellboremarkersets",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the Wellbore Markerset using osdu schema",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="post_wellboreMarkerset_osdu",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_wellboreMarkerset_osdu(
        wellboremarkersets: List[WellboreMarkerSet],
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=[to_record(w) for w in wellboremarkersets],
        data_partition_id=ctx.partition_id,
    )
