from fastapi import APIRouter, Depends, Header
import starlette.status as status
from starlette.responses import Response
from typing import List

from app.clients.storage_service_client import get_storage_record_service
from app.clients.search_service_client import get_search_service
from odes_storage.models import *
from app.model.model_curated import *
from app.utils import Context
from app.utils import get_ctx

import app.routers.ddms_v2.storage_helper as storage_helper

router = APIRouter()


@router.get('/wellbores/{wellboreid}', response_model=wellbore,
            summary="Get the Wellbore using wks:wellbore:1.0.6 schema",
            description="""Get the Wellbore object using its **id**.  <p>If the wellbore kind is
        *wks:wellbore:1.0.6* returns the record directly</p> <p>If the wellbore
        kind is different *wks:wellbore:1.0.6* it will get the raw record and
        convert the results to match the *wks:wellbore:1.0.6*. If convertion is
        not possible returns an error **500**""",
            operation_id="get_wellbore",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}})
async def get_wellbore(
        wellboreid: str,
        ctx: Context = Depends(get_ctx)
) -> wellbore:
    storage_service = await get_storage_record_service(ctx)
    wellboredict = await storage_service.get_record(id=wellboreid, data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:wellbore:1.0.6)
    return wellbore(**wellboredict.dict())


@router.delete('/wellbores/{wellboreid}',
               summary="Delete the wellbore. The API performs a logical deletion of the given record",
               operation_id="del_wellbore",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          }
               )
async def del_wellbore(
        wellboreid: str,
        recursive: bool = Header(False),
        ctx: Context = Depends(get_ctx)):
    storage_service = await get_storage_record_service(ctx)
    if recursive:
        await storage_helper.StorageHelper.delete_recursively(
            entity_id=wellboreid,
            relationship='wellbore',
            kind_list=["opendes:wks:logset:1.0.5", "opendes:wks:log:1.0.5", "opendes:wks:marker:1.0.4"],
            data_partition_id=ctx.partition_id,
            search_service=await get_search_service(ctx),
            storage_service=storage_service
        )
    else:
        await storage_service.delete_record(id=wellboreid, data_partition_id=ctx.partition_id)


@router.get('/wellbores/{wellboreid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the Wellbore",
            operation_id="get_wellbore_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}})
async def get_wellbore_versions(
        wellboreid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.get_all_record_versions(id=wellboreid, data_partition_id=ctx.partition_id)


@router.get('/wellbores/{wellboreid}/versions/{version}',
            response_model=wellbore,
            summary="Get the given version of the Wellbore using wks:wellbore:1.0.6 schema",
            description=""""Get the Wellbore object using its **id**.  <p>If the wellbore kind is
        *wks:wellbore:1.0.6* returns the record directly</p> <p>If the wellbore
        kind is different *wks:wellbore:1.0.6* it will get the raw record and
        convert the results to match the *wks:wellbore:1.0.6*. If convertion is
        not possible returns an error **500**""",
            operation_id="get_wellbore_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Wellbore not found"}})
async def get_wellbore_version(
        wellboreid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> wellbore:
    storage_service = await get_storage_record_service(ctx)
    result_wellbore = await storage_service.get_record_version(id=wellboreid,
                                                               version=version,
                                                               data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:wellbore:1.0.6)
    return wellbore(**result_wellbore.dict())


@router.put('/wellbores',
            response_model=CreateUpdateRecordsResponse,
            summary="Create or update the Wellbores using wks:wellbore:1.0.6 schema",
            operation_id="put_wellbore",
            responses={
                status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def put_wellbore(
        wellbores: List[wellbore],
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_service = await get_storage_record_service(ctx)

    # TODO: the following works 'by chance' because there's no manipulation
    #  and it only uses methods of BaseModel, but it's not rigorous
    return await storage_service.create_or_update_records(record=wellbores, data_partition_id=ctx.partition_id)
