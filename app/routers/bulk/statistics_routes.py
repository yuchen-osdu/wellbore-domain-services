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

from typing import Optional
from fastapi import Query

from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.context import Context, get_ctx

from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.record_utils import fetch_record
from app.routers.bulk.bulk_uri_dependencies import get_bulk_id_access, BulkIdAccess
from app.routers.bulk.utils import with_dask_blob_storage

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.errors import BulkRecordNotFound

from app.bulk_persistence.statistics.bulk_statistics import BulkStatistics
from app.bulk_persistence.statistics.models import BulkDataStatisticsResponse
from app.bulk_persistence.statistics import exceptions as statistics_exceptions

from app.helper.logger import get_logger
from app.helper.traces import TracingRoute

from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

router = APIRouter(route_class=TracingRoute)


async def fetch_record_info(ctx, bulk_uri_access, request, record_id, version):
    record = await fetch_record(ctx, record_id, version)
    if hasattr(request.state, 'version') and request.state.version != "V2":
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    try:
        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI') from e
    if not bulk_uri.is_valid():
        raise BulkRecordNotFound(record_id=record_id, bulk_id=None)

    return record, bulk_uri

responses_404_examples = {
            "description": "Not found",
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Record not found",
                            "value": {"detail": "Record not found"}
                        },
                        "data-not-found": {
                            "summary": "Statistics data not found",
                            "value": {
                                "errorType": "DATA_NOT_FOUND",
                                "message": "Statistics do not exist",
                            }
                        },
                        "stats-curves-error": {
                            "summary": "Requested curves unknown",
                            "value": {
                                "errorType": "CURVES_NOT_FOUND",
                                "message": "Requested curves unknown",
                            }
                        },
                        "stats-computation-error": {
                            "summary": "Computation still running",
                            "value": {
                                "errorType": "COMPUTATION_NOT_COMPLETE",
                                "message": "Statistics computation not finished yet",
                            }
                        },
                    }
                }
            }
        }

api_description_text = """
If wanted curves is an array:  
    - requests "ARRAY" retrieves all dimensions of the array  
    - requests "ARRAY[M:N]", retrieves all dimensions between M and N.
"""

api_unit_conversion_text = "No unit conversion is supported. Statistics will be returned using the same units" \
                           " as recorded in Curves[].CurveUnit"

api_supported_types_txt = """
Data types supported:  
            - int  
            - float  
            - date  
"""


@router.get(
    '/{record_id}/data/statistics',
    summary="Returns statistics of record's data for selected curves",
    description=f"""Returns the statistics on bulk data identified by the record in its last version. 

    {api_description_text}  
    
    {api_supported_types_txt}  
      
    {api_unit_conversion_text}
    """,
    response_model=BulkDataStatisticsResponse,
    responses={
        404: responses_404_examples
    }
)
async def get_bulk_statistics(
        request: Request,
        record_id: str,
        curves: Optional[str] = Query(default="",
                                      description='List of curves or array to be returned. All curves if empty',
                                      example='MD,GR'),
        ctx: Context = Depends(get_ctx),
        dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
):
    return await get_bulk_statistics_version(request=request,
                                             record_id=record_id,
                                             version=None,
                                             curves=curves,
                                             ctx=ctx,
                                             dask_blob_storage=dask_blob_storage,
                                             bulk_uri_access=bulk_uri_access)


class BulkStatisticsHTTPException(Exception):
    status_code: int
    error_type: str
    message = str

    def __init__(self, status_code: int, error_type: str, message: str):
        self.status_code = status_code
        self.error_type = error_type
        self.message = message

    def to_dict(self):
        return {'errorType': self.error_type, 'message': self.message}


async def http_stats_error_handler(request, e: BulkStatisticsHTTPException) -> JSONResponse:
    """
    Catches and handles pydantic validation errors
    """
    return JSONResponse(content=jsonable_encoder(e.to_dict()), status_code=e.status_code)


@router.get(
    '/{record_id}/versions/{version}/data/statistics',
    summary="Returns statistics of record's data for selected curves at requested version",
    response_model=BulkDataStatisticsResponse,
    description=f"""Returns the statistics on bulk data identified by the record and given version.  
    {api_description_text}  
      
    {api_supported_types_txt}  
    
    {api_unit_conversion_text}
    """,
    responses={
        404: responses_404_examples
    }
)
async def get_bulk_statistics_version(
        request: Request,
        record_id: str,
        version: str,
        curves: Optional[str] = Query(default="",
                                      description='List of curves or array to be returned. All curves if empty',
                                      example='MD,GR'),
        ctx: Context = Depends(get_ctx),
        dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
):
    # todo: refactor re-used code
    record = await fetch_record(ctx, record_id, version)
    if hasattr(request.state, 'version') and request.state.version != "V2":
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    try:
        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI') from e
    if not bulk_uri.is_valid():
        raise BulkRecordNotFound(record_id=record_id).raise_as_http()

    columns = filter(None, map(str.strip, curves.split(',')))
    columns = list(dict.fromkeys(columns))

    try:
        stats_df, stats_meta = await BulkStatistics(dask_blob_storage).get_bulk_statistics(record.id,
                                                                                           bulk_uri.bulk_id,
                                                                                           columns)
    except BulkRecordNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (statistics_exceptions.StatisticsNotFoundError,
            statistics_exceptions.RequestedCurvesError,
            statistics_exceptions.ComputationNotCompleteError) as e:
        raise BulkStatisticsHTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                          error_type=e.public_error_type,
                                          message=str(e))
    finally:
        get_logger().exception("get_bulk_statistics() has raised an exception")

    # only orient: 'index' or 'columns' cam be read with pd.DataFrame.from_dict().
    return BulkDataStatisticsResponse(**stats_meta.dict(), data=stats_df.to_dict(orient='index'))


@router.post(
    '/{record_id}/data/statistics',
    summary="Trigger computations of record's data statistics of record's data",
    description=f"""Trigger the computation of statistics on bulk data for 
    the record identified by the record_id at its last version   
      
    {api_unit_conversion_text}
    """,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Statistics or record not found"},
        status.HTTP_409_CONFLICT: {"description": "Statistics computation already started"},
        status.HTTP_200_OK: {"description": "Statistics computation started"},
    }
)
async def compute_bulk_statistics(
        request: Request,
        record_id: str,
        ctx: Context = Depends(get_ctx),
        dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)
):
    record = await fetch_record(ctx, record_id, None)
    if hasattr(request.state, 'version') and request.state.version != "V2":
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    try:
        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)  # TODO PATH logv2
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI') from e
    if not bulk_uri.is_valid():
        raise BulkRecordNotFound(record_id=record_id, bulk_id=None)

    try:
        await BulkStatistics(dask_blob_storage).compute_bulk_statistics(record.id, bulk_uri.bulk_id, record.version)
    except statistics_exceptions.ComputationRunningError as e:
        get_logger().exception("compute_bulk_statistics() has raised an exception")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
