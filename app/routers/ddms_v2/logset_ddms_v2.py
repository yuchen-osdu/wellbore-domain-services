from fastapi import APIRouter, Depends, Header
import starlette.status as status
from starlette.responses import Response

from app.clients.storage_service_client import get_storage_record_service
from app.clients.search_service_client import get_search_service
from odes_storage.models import *
from app.model.model_curated import *
from app.utils import Context
from app.utils import get_ctx

import app.routers.ddms_v2.storage_helper as storage_helper

router = APIRouter()


@router.get('/logsets/{logsetid}',
            response_model=logset,
            summary="Get the LogSet using wks:logSet:1.0.5 schema",
            description="""Get the LogSet object using its **id**""",
            operation_id="get_logset",
            responses={status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"}})
async def get_logset(
        logsetid: str,
        ctx: Context = Depends(get_ctx)
) -> logset:
    storage_service = await get_storage_record_service(ctx)
    logset_record = await storage_service.get_record(id=logsetid, data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:logSet:1.0.5)
    return logset(**logset_record.dict())


@router.delete('/logsets/{logsetid}',
               summary="Delete the LogSet. The API performs a logical deletion of the given record",
               operation_id="del_logset",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={
                   status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"},
                   status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
               })
async def del_logset(
        logsetid: str,
        recursive: bool = Header(False),
        ctx: Context = Depends(get_ctx)):
    storage_service = await get_storage_record_service(ctx)
    if recursive:
        await storage_helper.StorageHelper.delete_recursively(
            entity_id=logsetid,
            relationship='logset',
            kind_list=["opendes:wks:log:1.0.5"],
            data_partition_id=ctx.partition_id,
            search_service=await get_search_service(ctx),
            storage_service=storage_service
        )
    else:
        await storage_service.delete_record(id=logsetid, data_partition_id=ctx.partition_id)


@router.get('/logsets/{logsetid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the logset",
            operation_id="get_logset_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"}})
async def get_logset_versions(
        logsetid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.get_all_record_versions(id=logsetid, data_partition_id=ctx.partition_id)


@router.get('/logsets/{logsetid}/versions/{version}',
            response_model=logset,
            summary="Get the given version of LogSet using wks:logSet:1.0.5 schema",
            description=""""Get the LogSet object using its **id**.""",
            operation_id="get_logset_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "LogSet not found"}})
async def get_logset_version(
        logsetid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> logset:
    storage_service = await get_storage_record_service(ctx)
    result_logset = await storage_service.get_record_version(id=logsetid,
                                                             version=version,
                                                             data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:logSet:1.0.5)
    return logset(**result_logset.dict())


@router.post('/logsets/{logsetid}/harmonize',
             response_model=logset,
             summary="Create or update the LogSets using wks:logSet:1.0.5 schema",
             operation_id="harmonize_logset",
             responses={status.HTTP_404_NOT_FOUND: {"description": "logset not found"}})
async def harmonize_logset(logsetid: str) -> logset:
    return logset(id=logsetid, data=logSetData(operation="Harmonization"))


@router.put('/logsets',
            response_model=CreateUpdateRecordsResponse,
            summary="Create or update the LogSets using wks:logSet:1.0.5 schema",
            operation_id="put_logset",
            responses={
                status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def put_logset(
        logsets: List[logset],
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.create_or_update_records(record=logsets, data_partition_id=ctx.partition_id)

