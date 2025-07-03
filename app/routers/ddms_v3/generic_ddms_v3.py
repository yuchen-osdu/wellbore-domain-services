from typing import Callable, List

from fastapi import APIRouter, status, Depends, Body, HTTPException, Path, Response
from odes_storage.models import (
    Record, CreateUpdateRecordsResponse, RecordVersions
)
from pydantic import TypeAdapter, ValidationError
from starlette.requests import Request

from app.clients.storage_service_client import get_storage_record_service
from app.context import Context, get_ctx
from app.model.api_configuration import APIConfiguration
from app.model.osdu_record_id import split_record_id_version
from app.routers.bulk.bulk_routes_dependencies import BulkIdAccess, get_bulk_id_access
from app.routers.ddms_v3.ddms_v3_utils import get_api_config, DMSV3RouterUtils
from app.routers.delete.delete_bulk_data import delete_record
from app.routers.record_utils import fetch_record
from app.schemas import schema_library

router = APIRouter()
ConsistencyCheckFunction = Callable[[Record], None]

def validate_record_id(api_config: APIConfiguration = Depends(get_api_config),
        osdu_record_id: str = Path(...)
) -> str:
    """
    Validates the osdu_record_id against the provided id regex pattern
    Raises HTTPException(422) if validation fails.
    """
    try:
        return TypeAdapter(api_config.record_id_constraint).validate_python(osdu_record_id)
    except ValidationError as e:
        error_msg = ""
        for error_detail in e.errors():
            error_msg += error_detail.get('msg')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid recordID: {error_msg}"
        )


@router.get(
    "/{osdu_record_id}",
    response_model=Record,
    response_model_exclude_unset=True,
    summary="Get the record using the provided recordID",
    operation_id="get_osdu_record",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"}
    }
)
async def get_osdu_record(request: Request, osdu_record_id: str = Depends(validate_record_id),
                          ctx: Context = Depends(get_ctx)) -> Record:
    # Note: version is dropped here
    record_id, _ = split_record_id_version(osdu_record_id)
    storage_client = await get_storage_record_service(ctx)

    fetched_record = await storage_client.get_record(id=record_id, data_partition_id=ctx.partition_id)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(fetched_record, request.state)

    await schema_library.validate_records([fetched_record], ctx)
    return fetched_record


@router.delete(
    "/{osdu_record_id}",
    summary="Delete the record using id. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    operation_id="delete_osdu_record",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def delete_osdu_record(osdu_record_id: str = Depends(validate_record_id), ctx: Context = Depends(get_ctx),
                             purge: bool = False, bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)):

    await delete_record(record_id=osdu_record_id, purge=purge, ctx=ctx, bulk_uri_access=bulk_uri_access)


@router.get("/{osdu_record_id}/versions",
            response_model=RecordVersions,
            summary="Get all versions of the provided record",
            operation_id="get_record_versions",
            responses={
                status.HTTP_404_NOT_FOUND: {"description": "Record not found"}
            }
            )
async def get_record_versions(request: Request, osdu_record_id: str = Depends(validate_record_id),
                              ctx: Context = Depends(get_ctx)) -> RecordVersions:
    record = await fetch_record(ctx, osdu_record_id)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(id=osdu_record_id, data_partition_id=ctx.partition_id)

@router.get("/{osdu_record_id}/versions/{version}",
            response_model=Record,
            summary="Get specific version for the provided OSDU record",
            description="Get the specific version of object using its **id**. ",
            operation_id="get_specific_record_version",
            responses={
                status.HTTP_404_NOT_FOUND: {"description": "Record not found"}
            },
            response_model_exclude_unset=True,
            )
async def get_specific_record_version(version: int, request: Request, osdu_record_id: str = Depends(validate_record_id),
                                      ctx: Context = Depends(get_ctx)
) -> Record:
    storage_client = await get_storage_record_service(ctx)
    osdu_record = await storage_client.get_record_version(
        id=osdu_record_id, version=version, data_partition_id=ctx.partition_id
    )
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(osdu_record, request.state)
    await schema_library.validate_records([osdu_record], ctx)
    return osdu_record



@router.post("",
             response_model=CreateUpdateRecordsResponse,
             summary="Create or update record using osdu schema",
             operation_id="create_or_update_osdu_record",
             responses={
                 status.HTTP_400_BAD_REQUEST: {
                     "description": "Missing mandatory parameter or unknown parameter"
                 }
             },
             )
async def create_or_update_osdu_record(
        request: Request,
        input_records: List[Record] = Body(...),
        ctx: Context = Depends(get_ctx),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
        api_config: APIConfiguration = Depends(get_api_config)
) -> CreateUpdateRecordsResponse:
    await schema_library.validate_records(input_records, ctx)  # Checks the entities Vs their respective schemas
    DMSV3RouterUtils.raise_if_not_osdu_right_entities_kind(input_records,
                                                           request.state)  # Checks the kind of the entities is in the list of supported kinds of this API

    await DMSV3RouterUtils.raise_if_invalid_bulk_uri(input_records, bulk_uri_access)

    consistency_check_function: ConsistencyCheckFunction = api_config.record_consistency_check_function
    for idx, w in enumerate(input_records):
        consistency_check_function(w) # checking record level consistency

    storage_client = await get_storage_record_service(ctx)

    return await storage_client.create_or_update_records(
        record=input_records,
        data_partition_id=ctx.partition_id,
    )
