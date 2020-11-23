from fastapi import APIRouter, Depends, Header
import starlette.status as status
from starlette.responses import Response

from app.clients.storage_service_client import get_storage_record_service
from odes_storage.models import *
from app.model.model_curated import *
from app.utils import Context, get_ctx

router = APIRouter()


@router.get('/markers/{markerid}',
            response_model=marker,
            summary="Get the marker using wks:marker:1.0.4 schema",
            description="""Get the Marker object using its **id**""",
            operation_id="get_marker",
            responses={status.HTTP_404_NOT_FOUND: {"description": "marker not found"}})
async def get_marker(
        markerid: str,
        ctx: Context = Depends(get_ctx)
) -> marker:
    storage_service = await get_storage_record_service(ctx)
    marker_record = await storage_service.get_record(id=markerid, data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:marker:1.0.4)
    return marker(**marker_record.dict())


@router.delete('/markers/{markerid}',
               summary="Delete the marker. The API performs a logical deletion of the given record",
               operation_id="del_marker",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "Marker not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          }
               )
async def del_marker(
        markerid: str,
        recursive: bool = Header(False),
        ctx: Context = Depends(get_ctx)):
    storage_service = await get_storage_record_service(ctx)
    await storage_service.delete_record(id=markerid, data_partition_id=ctx.partition_id)


@router.get('/markers/{markerid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the marker",
            operation_id="get_marker_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "marker not found"}})
async def get_marker_versions(
        markerid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.get_all_record_versions(id=markerid, data_partition_id=ctx.partition_id)


@router.get('/markers/{markerid}/versions/{version}',
            response_model=marker,
            summary="Get the given version of marker using wks:marker:1.0.4 schema",
            operation_id="get_marker_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "marker not found"}})
async def get_marker_version(
        markerid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> marker:
    storage_service = await get_storage_record_service(ctx)
    result_marker = await storage_service.get_record_version(id=markerid,
                                                             version=version,
                                                             data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:marker:1.0.4)
    return marker(**result_marker.dict())


@router.put('/markers', response_model=CreateUpdateRecordsResponse,
            summary="Create or update the markers using wks:marker:1.0.4 schema",
            operation_id="put_marker",
            responses={
                status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def put_marker(
        markers: List[marker],
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.create_or_update_records(record=markers,
                                                          data_partition_id=ctx.partition_id)
