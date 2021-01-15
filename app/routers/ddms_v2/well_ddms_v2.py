from fastapi import APIRouter, Depends, Query
import starlette.status as status
from starlette.responses import Response

from app.clients.storage_service_client import get_storage_record_service
from app.clients.search_service_client import get_search_service
from odes_storage.models import *
from app.model.model_curated import *
from app.utils import Context
from app.utils import get_ctx
from app.model.model_utils import to_record, from_record
from app.model.entity_utils import Entity

import app.routers.ddms_v2.storage_helper as storage_helper

router = APIRouter()


@router.get('/wells/{wellid}', response_model=well,
            summary="Get the Well using wks:well:1.0.2 schema",
            description="""Get the Well object using its **id**.  <p>If the well kind is
        *wks:well:1.0.2* returns the record directly</p> <p>If the well
        kind is different *wks:well:1.0.2* it will get the raw record and
        convert the results to match the *wks:well:1.0.2*. If convertion is
        not possible returns an error **500**""",
            operation_id="get_well",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Well not found"}})
async def get_well(
        wellid: str,
        ctx: Context = Depends(get_ctx)
) -> well:
    storage_client = await get_storage_record_service(ctx)
    well_record = await storage_client.get_record(id=wellid, data_partition_id=ctx.partition_id)
    return from_record(well, well_record)


@router.delete('/wells/{wellid}',
               summary="Delete the well. The API performs a logical deletion of the given record",
               operation_id="del_well",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "Well not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          }
               )
async def del_well(
        wellid: str,
        recursive: bool = Query(default=False, description="Whether or not to delete records children"),
        ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    if recursive:

        sub_entity_types = [
            Entity.WELLBORE,
            Entity.LOGSET,
            Entity.LOG,
            Entity.MARKER,
            Entity.TRAJECTORY,
            Entity.DIPSET
        ]

        await storage_helper.StorageHelper.delete_recursively(
            ctx,
            entity_id=wellid,
            relationship='well',
            entity_list=sub_entity_types,
            data_partition_id=ctx.partition_id,
            search_service=await get_search_service(ctx),
            storage_service=storage_client
        )
    else:
        await storage_client.delete_record(id=wellid, data_partition_id=ctx.partition_id)


@router.get('/wells/{wellid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the Well",
            operation_id="get_well_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Well not found"}})
async def get_well_versions(
        wellid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=wellid, data_partition_id=ctx.partition_id)


@router.get('/wells/{wellid}/versions/{version}',
            response_model=well,
            summary="Get the given version of the Well using wks:well:1.0.2 schema",
            description=""""Get the Well object using its **id**.  <p>If the well kind is
        *wks:well:1.0.2* returns the record directly</p> <p>If the well
        kind is different *wks:well:1.0.2* it will get the raw record and
        convert the results to match the *wks:well:1.0.2*. If convertion is
        not possible returns an error **500**""",
            operation_id="get_well_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Well not found"}})
async def get_well_version(
        wellid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> well:
    storage_client = await get_storage_record_service(ctx)
    well_record = await storage_client.get_record_version(id=wellid,
                                                          version=version,
                                                          data_partition_id=ctx.partition_id)
    return from_record(well, well_record)


@router.post('/wells',
             response_model=CreateUpdateRecordsResponse,
             summary="Create or update the Wells using wks:well:1.0.2 schema",
             operation_id="post_well",
             responses={
                 status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def post_well(
        wells: List[well],
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[to_record(w) for w in wells],
        data_partition_id=ctx.partition_id)
