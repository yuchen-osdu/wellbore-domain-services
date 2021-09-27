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

import asyncio
import json
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Response,
    status,
    Body
)
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    RecordVersions,
)
from pydantic import BaseModel, Field

from app.bulk_persistence import DataframeSerializerAsync, DataframeSerializerSync, JSONOrient, MimeTypes, get_dataframe
from app.clients.storage_service_client import get_storage_record_service
from app.model.log_bulk import LogBulkHelper
from app.model.model_curated import log
from app.model.model_utils import from_record, to_record
from app.routers.ddms_v2.persistence import Persistence
from app.routers.common_parameters import json_orient_parameter, REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.record_utils import fetch_record, update_records
from app.utils import Context, OpenApiHandler, OpenApiResponse, get_ctx, load_schema_example


router = APIRouter()

LOGS_API_BASE_PATH = '/logs'

async def get_persistence() -> Persistence:
    return Persistence()


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log META -----------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.get('/logs/{logid}',
            response_model=log,
            summary="Get the Log using wks:log:1.0.5 schema",
            description="""Get the log object using its data ecosystem **id**.  <p>If the log
                kind is *wks:log:1.0.5* returns the record directly</p> <p>If the
                wellbore kind is different *wks:log:1.0.5* it will get the raw
                record and convert the results to match the *wks:log:1.0.5*. If
                conversion is not possible returns an error **500**.</p>{}""".format(REQUIRED_ROLES_READ),
            operation_id="get_log",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}},
            response_model_exclude_unset=True)
async def get_log(
        logid: str,
        ctx: Context = Depends(get_ctx)
) -> log:
    record = await fetch_record(ctx, logid)
    return from_record(log, record)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API create or update Log META ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.post('/logs', response_model=CreateUpdateRecordsResponse,
             summary="Create or update the logs using wks:log:1.0.5 schema",
             description="{}".format(REQUIRED_ROLES_WRITE),
             operation_id="post_log",
             responses={
                 status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}})
async def post_log(
        logs: List[log] = Body(..., example= load_schema_example("log_v2.json")),
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    if len(logs) == 0:
        return CreateUpdateRecordsResponse(recordCount=0, recordIds=[])

    return await update_records(ctx, records=[to_record(lg) for lg in logs])


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------- API delete Log META ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.delete('/logs/{logid}',
               summary="Delete the log. The API performs a logical deletion of the given record",
               description="{}".format(REQUIRED_ROLES_WRITE),
               operation_id="del_log",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          })
async def del_log(
        logid: str,
        ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(id=logid, data_partition_id=ctx.partition_id)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log all versions ---------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.get(
    "/logs/{logid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the log",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_log_versions",
    responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}}
)
async def get_log_versions(
    logid: str, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=logid, data_partition_id=ctx.partition_id
    )


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- API get Log @ specific version ---------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------


@router.get(
    "/logs/{logid}/versions/{version}",
    response_model=log,
    summary="Get the given version of log using wks:log:1.0.5 schema",
    description="{}".format(REQUIRED_ROLES_READ),
    operation_id="get_log_version",
    responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}},
    response_model_exclude_unset=True
)
async def get_log_version(
    logid: str, version: int, ctx: Context = Depends(get_ctx)
) -> log:
    return from_record(log, await fetch_record(ctx, logid, version))


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------- API write Log BULK ---------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
def bulk_id_path_parameter(bulk_path: str = Query(
    None,
    alias='bulk-path',
    description='The json path to the bulk reference (see https://goessner.net/articles/JsonPath/). '
                'Required for non wks:log.')
) -> str:
    return bulk_path


async def _write_log_data(
        ctx: Context,
        persistence: Persistence,
        logid: str,
        bulk_path: Optional[str],
        dataframe: pd.DataFrame) -> CreateUpdateRecordsResponse:
    # TODO: handle strings - if column type is object or string, could be useful to
    # convert to categories df['text'].astype('category') to speed up storage
    # http://matthewrocklin.com/blog/work/2015/03/16/Fast-Serialization

    # we can concurrently fetch the log record and construct/upload the bulk
    bulk_id, log_record = await asyncio.gather(
        persistence.write_bulk(ctx=ctx, dataframe=dataframe),
        fetch_record(ctx, logid),
    )
    # update the record
    LogBulkHelper.update_bulk_id(log_record, bulk_id, bulk_path)

    # push new version on the storage
    return await update_records(ctx, [log_record])


_log_dataframe_example = pd.DataFrame(
    [
        [0, 1001, 2001],
        [0.5, 1002, 2002],
        [1, 1003, 2003],
        [1.5, 1004, 2004],
        [2, 1005, 2005],
    ],
    columns=["Ref", "col_100X", "col_200X"],
)

# manually setup doc as we wanted to tweaked the classic mechanism in order to best perf as we can
@OpenApiHandler.set(
    operation_id="write_log_data",
    request_body={
        'description':
            'Write log bulk data.'
            '\nIt uses [Pandas.Dataframe json format]'
            '(https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html)' +
            '.\n Here\'re examples for data with {} rows and {} columns with different _orient_: '.format(
                _log_dataframe_example.shape[0],
                _log_dataframe_example.shape[1]) +
            ''.join([f'\n* {o.value}:  <br/>`{DataframeSerializerSync.to_json(_log_dataframe_example, o)}`<br/>&nbsp;'
                     for o in JSONOrient]),
        # put examples here because of bug in swagger UI to properly render multiple examples
        'required': True,
        'content': {
            MimeTypes.JSON.type: {
                'schema': {
                    # swagger UI bug, so single example here
                    'example': json.loads(
                        DataframeSerializerSync.to_json(_log_dataframe_example, JSONOrient.split)
                    ),
                    'oneOf': [DataframeSerializerSync.get_schema(o) for o in JSONOrient]
                }
            }
        }
    })
@router.post('/logs/{logid}/data',
             summary="Writes the specified data to the log (atomic).",
             description='Overwrite if exists. {}'.format(REQUIRED_ROLES_WRITE),
             operation_id="write_log_data",
             response_model=CreateUpdateRecordsResponse,
             responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                        status.HTTP_200_OK: {}})
async def write_log_data(
    request: Request,
    logid: str,
    orient: JSONOrient = Depends(json_orient_parameter),
    bulk_path: str = Depends(bulk_id_path_parameter),
    persistence: Persistence = Depends(get_persistence),
    ctx: Context = Depends(get_ctx),
) -> CreateUpdateRecordsResponse:
    content = await request.body()  # request.stream()
    df = await DataframeSerializerAsync().read_json(content, orient)
    return await _write_log_data(ctx, persistence, logid, bulk_path, df)

# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------- API write Log BULK (UPLOAD FILE) -------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.post('/logs/{logid}/upload_data',
             summary='Writes the data to the log. Support json file (then orient must be provided) and parquet',
             description='Overwrite if exists. {}'.format(REQUIRED_ROLES_WRITE),
             operation_id="upload_log_data",
             response_model=CreateUpdateRecordsResponse,
             responses={
                 status.HTTP_400_BAD_REQUEST: {"description": "invalid request"},
                 status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                 status.HTTP_200_OK: {}})
async def upload_log_data_file(
    logid: str,
    file: UploadFile = File(...),
    orient: JSONOrient = Depends(json_orient_parameter),
    bulk_path: str = Depends(bulk_id_path_parameter),
    persistence: Persistence = Depends(get_persistence),
    ctx: Context = Depends(get_ctx),
) -> CreateUpdateRecordsResponse:
    try:
        mime_type = MimeTypes.from_str(file.content_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unknown content_type " + file.content_type,
        )

    if mime_type == MimeTypes.JSON:
        # TODO for now the entire content is read at once, can chunk it instead I guess
        content: bytes = await file.read()
        df = await DataframeSerializerAsync().read_json(content, orient)
    elif mime_type == MimeTypes.PARQUET:
        try:
            data = await file.read()
            df = await DataframeSerializerAsync().read_parquet(data)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='invalid data: ' + e.message if hasattr(e, 'message') else 'unknown error')
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=file.content_type + ' is not supported')

    return await _write_log_data(ctx, persistence, logid, bulk_path, df)


async def _get_log_data(
    ctx: Context,
    persistence: Persistence,
    logid: str,
    version: int,
    orient: JSONOrient,
    bulk_id_path: str = None,
):

    """
        Get log bulk data in format in the given orient value from log id logid

        private method in order to  factorize GET /logs/{logid} and GET /logs/{logid}/version/{version}
        get the log record with the specified log id into the storage,
        fetch the bulk id in the record using bulk_id_path if any
        read the bulk data and serialize it into a json.

        param persistence: persistence instance used to read the data
        param logid: id of the log
        param version:  the version of the data log you want to have
        param orient:  get the log data in the given orient value
        param bulk_id_path: support of custom  bulk id path, if none use the standard

        return json response with the bulk data in the orient format
    """

    # we may use an optimistic cache here
    log_record = await fetch_record(ctx, logid, version)

    df = await persistence.read_bulk(ctx, log_record, bulk_id_path)
    content = await DataframeSerializerAsync().to_json(df, orient=orient)
    return Response(content=content, media_type=MimeTypes.JSON.type) #  content is already jsonified no need to use JSONResponse


@OpenApiHandler.set(
    operation_id="get_log_data",
    responses=[
        OpenApiResponse(
            status=status.HTTP_200_OK,
            description=
            'Get log bulk data in format in the given _orient_ value.'
            '\nIt uses [Pandas.Dataframe json format]'
            '(https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html)' +
            '.\n Here\'re examples for data with {} rows and {} columns with different _orient_: '.format(
                _log_dataframe_example.shape[0],
                _log_dataframe_example.shape[1]) +
            ''.join([f'\n* {o.value}:  <br/>`{DataframeSerializerSync.to_json(_log_dataframe_example, o)}`<br/>&nbsp;'
                     for o in JSONOrient]),

            name='GetLogDataResponse',
            example=DataframeSerializerSync.to_json(_log_dataframe_example, JSONOrient.split),
            schema={'oneOf': [DataframeSerializerSync.get_schema(o) for o in JSONOrient]})
    ])
@router.get('/logs/{logid}/data',
            summary="Returns all data within the specified filters. Strongly consistent.",
            description='return full bulk data. {}'.format(REQUIRED_ROLES_READ),
            operation_id="get_log_data",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}})
async def get_log_data(
    logid: str,
    orient: JSONOrient = Depends(json_orient_parameter),
    bulk_id_path: str = Depends(bulk_id_path_parameter),
    persistence: Persistence = Depends(get_persistence),
    ctx: Context = Depends(get_ctx)
):
    return await _get_log_data(
        ctx=ctx,
        persistence=persistence,
        logid=logid,
        orient=orient,
        bulk_id_path=bulk_id_path,
        version=None
    )


class StatsColumn(BaseModel):
    count: int = Field(..., description="Count number of non-NA/null observations")
    mean: float = Field(..., description="Mean of the values")
    std: float = Field(..., description="Standard deviation of the observations")
    min: float = Field(..., description="Minimum of the values in the object")
    percentile25: float = Field(..., alias="25%")
    percentile50: float = Field(..., alias="50%")
    percentile75: float = Field(..., alias="75%")
    max: float = Field(..., description="Maximum of the values in the object")


@router.get('/logs/{logid}/statistics',
            summary='Data statistics',
            description="This API will return count, mean, std, min, max and percentiles of each column. {}"
            .format(REQUIRED_ROLES_READ),
            response_model=Dict[str, StatsColumn],
            )
async def get_log_data_statistics(logid: str,
                                  bulk_id_path: str = Depends(bulk_id_path_parameter),
                                  ctx: Context = Depends(get_ctx)):
    """
    /!\ This is a non optimized API due to the the fetch of the entire bulk each time it is called
    In case of intensive usage, this API should retrieve statistics from metadata stored at write time.
    """
    # we may use an optimistic cache here
    log_record = await fetch_record(ctx, logid)  # use dict to support the custom path

    bulk_id, _prefix = LogBulkHelper.get_bulk_id(log_record, bulk_id_path)
    if bulk_id is None:
        content = '{}'  # no bulk
    else:
        df = await get_dataframe(ctx, bulk_id)
        content = df.describe(include="all").to_json()

    return Response(content=content, media_type=MimeTypes.JSON.type)


@OpenApiHandler.set(
    operation_id="get_log_data_by_version",
    responses=[
        OpenApiResponse(
            status=status.HTTP_200_OK,
            description=
            'Get log bulk data in format in the given _orient_ value.'
            '\nIt uses [Pandas.Dataframe json format]'
            '(https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html)' +
            '.\n Here\'re examples for data with {} rows and {} columns with different _orient_: '.format(
                _log_dataframe_example.shape[0],
                _log_dataframe_example.shape[1]) +
            ''.join([f'\n* {o.value}:  <br/>`{DataframeSerializerSync.to_json(_log_dataframe_example, o)}`<br/>&nbsp;'
                     for o in JSONOrient]),

            name='GetLogDataResponse',
            example=DataframeSerializerSync.to_json(_log_dataframe_example, JSONOrient.split),
            schema={'oneOf': [DataframeSerializerSync.get_schema(o) for o in JSONOrient]})
    ])
@router.get('/logs/{logid}/versions/{version}/data',
            summary="Returns all data within the specified filters. Strongly consistent.",
            description='return full bulk data. {}'.format(REQUIRED_ROLES_READ),
            operation_id="get_log_data_by_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "log not found"}})
async def get_log_data_by_version(
    logid: str,
    version: int,
    orient: JSONOrient = Depends(json_orient_parameter),
    bulk_id_path: str = Depends(bulk_id_path_parameter),
    persistence: Persistence = Depends(get_persistence),
    ctx: Context = Depends(get_ctx),
):

    return await _get_log_data(
        ctx=ctx,
        persistence=persistence,
        logid=logid,
        orient=orient,
        bulk_id_path=bulk_id_path,
        version=version,
    )


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------- NOT IMPLEMENTED ---------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

@router.get('/logs/{logid}/decimated',
            summary="Returns a decimated version of all data within the specified filters. Eventually consistent.",
            description="""TODO
            Note: row order is not preserved. {}""".format(REQUIRED_ROLES_READ),
            operation_id="get_log_decimated",
            responses={
                status.HTTP_404_NOT_FOUND: {"description": "log not found"},
                status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "log is not compatible with decimation"}
            })
async def get_log_decimated(
        logid: str,
        quantiles: int = Query(None, description="Number of division desired"),
        start: float = Query(None, description="The start value for the log decimation"),
        stop: float = Query(None, description="The stop value for the log decimation"),
        orient: str = Query("values",
                            description='response format JSON. Only "values" is allowed.',
                            regex="values"),
        bulk_id_path: str = Depends(bulk_id_path_parameter),
        persistence: Persistence = Depends(get_persistence),
        ctx: Context = Depends(get_ctx)):
    log_record = await fetch_record(ctx, logid)

    df = await persistence.read_bulk(ctx, log_record, bulk_id_path)

    # TODO : remove this after review what should be done with index column
    if len(df.columns) == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="data frame doesn't contain index")

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
