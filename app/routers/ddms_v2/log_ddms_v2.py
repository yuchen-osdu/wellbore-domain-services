import asyncio
import io
from typing import Optional, List, Union

import pandas as pd
import numpy as np
import starlette.status as status
from starlette.responses import Response
from fastapi import APIRouter, Depends, HTTPException, Query, Request, File, UploadFile
from pydantic import BaseModel

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from app.clients import StorageRecordServiceClient
from app.clients.storage_service_client import get_storage_record_service
from odes_storage.models import CreateUpdateRecordsResponse, Record, RecordVersions

from app.model.model_curated import log
from app.storage.dataframe_serializer import DataframeSerializer, JSONOrient
from app.model.log_bulk import LogBulkHelper
from app.storage.blob_storage import create_and_write_blob, BlobFileExporters, read_blob, BlobBulk
from app.storage.mime_types import MimeTypes
from app.storage.tenant_provider import resolve_tenant
from app.utils import Context, OpenApiHandler, OpenApiResponse

router = APIRouter()


def get_ctx() -> Context:
    return Context.current()


async def create_and_store_dataframe(ctx: Context, df: pd.DataFrame) -> str:
    """Store bulk on a blob storage"""
    new_bulk_id = LogBulkHelper.new_bulk_id()
    tenant = await resolve_tenant(ctx.partition_id)
    async with create_and_write_blob(df,
                                     file_exporter=BlobFileExporters.PARQUET,
                                     blob_id=new_bulk_id) as bulkblob:
        storage: BlobStorageBase = await ctx.app_injector.get(BlobStorageBase)
        await storage.upload(tenant.project_id,
                             tenant.bucket_name,
                             bulkblob.id,
                             bulkblob.data,
                             content_type=bulkblob.content_type,
                             metadata=bulkblob.metadata)
        return bulkblob.id


async def get_log_dataframe(ctx: Context, bulk_id: str) -> pd.DataFrame:
    """ fetch bulk from a blob storage, provide column major """
    tenant = await resolve_tenant(ctx.partition_id)
    storage: BlobStorageBase = await ctx.app_injector.get(BlobStorageBase)

    bytes_data = await storage.download(tenant.project_id, tenant.bucket_name, bulk_id)
    # for now use fix parquet format saving one call
    # meta_data = await storage.download_metadata(tenant.project_id, tenant.bucket_name, bulk_id)
    # content_type = meta_data.metadata["content_type"]
    blob = BlobBulk(id=bulk_id, data=io.BytesIO(bytes_data), content_type=MimeTypes.PARQUET.type)
    data_frame = await read_blob(blob)
    return data_frame


async def fetch_record(ctx: Context, record_id: str) -> Record:
    """
    :param ctx: context
    :param record_id: record identifier
    :return: record
    """

    srv = await get_storage_record_service(ctx)
    return await srv.get_record(id=record_id, data_partition_id=ctx.partition_id)


async def update_records(ctx: Context, records: List[Union[BaseModel, dict]]) -> CreateUpdateRecordsResponse:
    """
    Can manipulate both pydantic model or dict
    :param ctx: context
    :param records: list of record in dict or pydantic format
    :return: id of the record
    """
    srv = await get_storage_record_service(ctx)
    # record_dict_list = [r.dict(exclude_unset=True) if isinstance(r, BaseModel) else r for r in records]
    # just assume it works
    return await srv.create_or_update_records(record=records, data_partition_id=ctx.partition_id)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log META -----------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.get('/logs/{logid}',
            response_model=log,
            summary="Get the Log using wks:log:1.0.5 schema",
            description="""
                Get the log object using its data ecosystem **id**.  <p>If the log
                kind is *wks:log:1.0.5* returns the record directly</p> <p>If the
                wellbore kind is different *wks:log:1.0.5* it will get the raw
                record and convert the results to match the *wks:log:1.0.5*. If
                conversion is not possible returns an error **500**</p>""",
            operation_id="get_log",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}})
async def get_log(
        logid: str,
        ctx: Context = Depends(get_ctx)
) -> log:
    record = await fetch_record(ctx, logid)
    return log(**record.dict())


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API create or update Log META ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.put('/logs', response_model=CreateUpdateRecordsResponse,
            summary="Create or update the logs using wks:log:1.0.5 schema",
            operation_id="put_log",
            responses={
                status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def put_log(
        logs: List[log],
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    if len(logs) == 0:
        return CreateUpdateRecordsResponse(recordCount=0, recordIds=[])
    srv = await get_storage_record_service(ctx)
    return await srv.create_or_update_records(record=logs, data_partition_id=ctx.partition_id)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------- API delete Log META ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.delete('/logs/{logid}',
               summary="Delete the log. The API performs a logical deletion of the given record",
               operation_id="del_log",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          })
async def del_log(
        logid: str,
        ctx: Context = Depends(get_ctx)):
    storage = await get_storage_record_service(ctx)
    await storage.delete_record(id=logid, data_partition_id=ctx.partition_id)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log all versions ---------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.get('/logs/{logid}/versions', response_model=RecordVersions,
            summary="Get all versions of the log",
            operation_id="get_log_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}})
async def get_log_versions(
        logid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage = await get_storage_record_service(ctx)
    return await storage.get_all_record_versions(id=logid,
                                                 data_partition_id=ctx.partition_id)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log @ specific version ---------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

@router.get('/logs/{logid}/versions/{version}', response_model=log,
            summary="Get the given version of log using wks:log:1.0.5 schema",
            operation_id="get_log_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}})
async def get_log_version(
        logid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> log:
    storage = await get_storage_record_service(ctx)
    record = await storage.get_record_version(id=logid,
                                              version=version,
                                              data_partition_id=ctx.partition_id)
    return log(**record.dict())


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------- API write Log BULK ---------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

def json_orient_parameter(orient: str = Query(
    JSONOrient.split.value,
    description='define format when using JSON data is used. Value can be ' + ', '.join([o.value for o in JSONOrient]))
) -> str:
    return orient


def bulk_id_path_parameter(bulk_path: str = Query(
    None,
    alias='bulk-path',
    description='The json path to the bulk reference (see https://goessner.net/articles/JsonPath/). '
                'Required for non wks:log.')
) -> str:
    return bulk_path


async def _write_log_data(ctx: Context, logid: str, bulk_path: Optional[str], dataframe) -> CreateUpdateRecordsResponse:
    # TODO: handle strings - if column type is object or string, could be useful to
    # convert to categories df['text'].astype('category') to speed up storage
    # http://matthewrocklin.com/blog/work/2015/03/16/Fast-Serialization

    # we can concurrently fetch the log record and construct/upload the bulk
    bulk_id, log_record_dict = await asyncio.gather(
        create_and_store_dataframe(ctx, dataframe),
        fetch_record(ctx, logid)
    )

    # update the record
    LogBulkHelper.update_bulk_id(log_record_dict, bulk_id, bulk_path)

    # push new version on the storage
    return await update_records(ctx, [log_record_dict])


# manually setup doc as we wanted to tweaked the classic mechanism in order to best perf as we can
@OpenApiHandler.set(
    operation_id="write_log_data",
    request_body={
        'description': 'bulk data provides in format corresponding to the _orient_ value:  ' +
                       ''.join([f'\n* {o.value}: {DataframeSerializer.example_as_json(o)}' for o in JSONOrient]),
        # put examples here because of bug in swagger UI to properly render multiple examples
        'required': True,
        'content': {
            MimeTypes.JSON.type: {
                'schema': {
                    # swagger UI bug, so single example here
                    'example': DataframeSerializer.example_as_dict(JSONOrient.split),
                    'oneOf': [DataframeSerializer.get_schema(o) for o in JSONOrient]
                }
            }
        }
    })
@router.put('/logs/{logid}/data',
            summary="Writes the specified data to the log (atomic).",
            description='Overwrite if exists',
            operation_id="write_log_data",
            response_model=CreateUpdateRecordsResponse,
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                       status.HTTP_200_OK: {}})
async def write_log_data(
        request: Request,
        logid: str,
        orient: str = Depends(json_orient_parameter),
        bulk_path: str = Depends(bulk_id_path_parameter),
        ctx: Context = Depends(get_ctx)) -> CreateUpdateRecordsResponse:
    content = await request.body()  # request.stream()
    df = DataframeSerializer.read_json(content, orient)
    return await _write_log_data(ctx, logid, bulk_path, df)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------- API write Log BULK (UPLOAD FILE) -------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.put('/logs/{logid}/upload_data',
            summary='Writes the data to the log. Support json file (then orient must be provided) and parquet',
            description='Overwrite if exists',
            operation_id="upload_log_data",
            response_model=CreateUpdateRecordsResponse,
            responses={
                status.HTTP_400_BAD_REQUEST: {"description": "invalid request"},
                status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                status.HTTP_200_OK: {}})
async def upload_log_data_file(
        logid: str,
        file: UploadFile = File(...),
        orient: str = Depends(json_orient_parameter),
        bulk_path: str = Depends(bulk_id_path_parameter),
        ctx: Context = Depends(get_ctx)) -> CreateUpdateRecordsResponse:
    try:
        mime_type = MimeTypes.from_str(file.content_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown content_type " + file.content_type)

    if mime_type == MimeTypes.JSON:
        # TODO for now the entire content is read at once, can chunk it instead I guess
        content: bytes = await file.read()
        df = DataframeSerializer.read_json(content, orient)
    elif mime_type == MimeTypes.PARQUET:
        try:
            df = DataframeSerializer.read_parquet(file.file)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='invalid data: ' + e.message if hasattr(e, 'message') else 'unknown error')
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=file.content_type + ' is not supported')

    return await _write_log_data(ctx, logid, bulk_path, df)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- API read Log BULK ---------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

@OpenApiHandler.set(
    operation_id="get_log_data",
    responses=[
        OpenApiResponse(status=status.HTTP_200_OK,
                        description='bulk data',
                        name='GetLogDataResponse',
                        example=DataframeSerializer.example_as_dict(JSONOrient.split),
                        schema={'oneOf': [DataframeSerializer.get_schema(o) for o in JSONOrient]})
    ])
@router.get('/logs/{logid}/data',
            summary="Returns all data within the specified filters. Strongly consistent.",
            description='return full bulk data',
            operation_id="get_log_data",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}})
async def get_log_data(
        logid: str,
        orient: str = Depends(json_orient_parameter),
        bulk_id_path: str = Depends(bulk_id_path_parameter),
        ctx: Context = Depends(get_ctx)):
    # we may use an optimistic cache here
    log_record = await fetch_record(ctx, logid)  # use dict to support the custom path

    bulk_id = LogBulkHelper.get_bulk_id(log_record, bulk_id_path)
    if bulk_id is None:
        content = '{}'  # no bulk
    else:
        df = await get_log_dataframe(ctx, bulk_id)
        content = DataframeSerializer.to_json(df, orient=orient)

    return Response(content=content, media_type=MimeTypes.JSON.type)


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------- NOT IMPLEMENTED ---------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

@router.get('/logs/{logid}/decimated',
            summary="Returns a decimated version of all data within the specified filters. Eventually consistent.",
            description="""TODO
            Note: row order is not preserved.""",
            operation_id="get_log_decimated",
            responses={
                status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "log is not compatible with decimation"}
            })
async def get_log_decimated(
        logid: str,
        quantiles: int,
        start: float = None,
        stop: float = None,
        method: str = None,  # TODO: we could have various decimation methods
        orient: str = Depends(json_orient_parameter),
        bulk_id_path: str = Depends(bulk_id_path_parameter),
        ctx: Context = Depends(get_ctx)):
    log_record = await fetch_record(ctx, logid)  # use dict to support the custom path

    bulk_id = LogBulkHelper.get_bulk_id(log_record, bulk_id_path)
    if bulk_id is None:
        df = pd.DataFrame()  # no bulk
    else:
        df = await get_log_dataframe(ctx, bulk_id)

    if df.dtypes[1] not in [np.float64, np.float32]:
        raise HTTPException(status_code=422, detail="log is not compatible with decimation")

    # TODO: Make this async using dask distributed?

    if start is not None and stop is not None:
        # get values between start and stop
        window = df.set_index(0)[start:stop].reset_index()
    else:
        window = df
    # create groups
    res = pd.qcut(window[0], q=quantiles)
    groups = window.groupby([res])
    # get mean for each group
    means = groups.mean()[[0, 1]]
    # serialize
    content = means.fillna("NaN").to_json(orient=orient)

    return Response(content=content, media_type=MimeTypes.JSON.type)
