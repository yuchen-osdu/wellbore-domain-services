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

from typing import Optional, List
from fastapi.encoders import jsonable_encoder
from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import JSONResponse
from odes_storage.models import Record

from app.routers.record_utils import fetch_record_dependency, fetch_latest_version_record_dependency
from app.routers.bulk.bulk_routes_dependencies import get_bulk_id_access, BulkIdAccess, get_bulk_io_read
from app.bulk_persistence.dask.dataframe_render import DataFrameRender

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.errors import BulkRecordNotFound, BulkCurvesNotFound
from app.bulk_persistence import BulkStatistics, BulkDataStatisticsResponse, exceptions as statistics_exceptions
from app.bulk_persistence import model_chunking
# from app.bulk_persistence.statistics.bulk_statistics_wdms_worker import BulkStatisticWdmsWorker

from app.bulk_persistence import async_load_bulk_catalog_with_blob_storage
from app.bulk_persistence import BulkIO

from app.helper.traces import TracingRoute, with_trace
from app.context import get_ctx

from app.conf import Config
from app.model.osdu_record_id import WellLogId
from app.context import Context, get_ctx
from app.utils import get_http_client_session


router = APIRouter(route_class=TracingRoute)

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


@with_trace("with_dask_blob_storage")
async def with_dask_blob_storage() -> DaskBulkStorage:
    return await get_ctx().app_injector.get(DaskBulkStorage)


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
        record_id: WellLogId,
        record: Record = Depends(fetch_latest_version_record_dependency),
        curves: Optional[str] = Query(default=None,
                                      description='List of curves or array to be returned. All curves if empty',
                                      examples=model_chunking.curves_examples),
        bulk_io: BulkIO = Depends(get_bulk_io_read),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
        ctx: Context = Depends(get_ctx),
):
    return await get_bulk_statistics_version(request=request,
                                             record_id=record_id,
                                             record=record,
                                             version=None,
                                             curves=curves,
                                             bulk_io=bulk_io,
                                             bulk_uri_access=bulk_uri_access,
                                             ctx=ctx)


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


# async def get_statistics_with_dask(dask_blob_storage, catalog, record_id: str, bulk_uri: str, columns: List[str]):
#     """ Get bulk data statistics using Dask storage to access data """
#     try:
#         stats_df, stats_meta = await BulkStatistics(dask_blob_storage).get_bulk_statistics(catalog, record_id,
#                                                                                            bulk_uri, columns)
#     except BulkRecordNotFound as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except (statistics_exceptions.StatisticsNotFoundError,
#             statistics_exceptions.RequestedCurvesError,
#             statistics_exceptions.ComputationNotCompleteError) as e:
#         raise BulkStatisticsHTTPException(status_code=status.HTTP_404_NOT_FOUND, error_type=e.public_error_type,
#                                           message=str(e))
#
#     # replace np.nan by string "NaN" to have unified str type values for std column
#     if not stats_df.empty:
#         stats_df['std'].fillna(value=str("NaN"), inplace=True)
#
#     # only orient: 'index' or 'columns' cam be read with pd.DataFrame.from_dict().
#     return BulkDataStatisticsResponse(**stats_meta.dict(by_alias=True), data=stats_df.to_dict(orient='index'))


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
        record_id: WellLogId,
        version: int,
        record: Record = Depends(fetch_record_dependency),
        curves: Optional[str] = Query(default=None,
                                      description='List of curves or array to be returned. All curves if empty',
                                      examples=model_chunking.curves_examples),
        bulk_io: BulkIO = Depends(get_bulk_io_read),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
        ctx: Context = Depends(get_ctx),
):
    try:
        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI') from e
    if not bulk_uri.is_valid():
        raise BulkRecordNotFound(record_id=record.id).raise_as_http()

    curves_selection = []
    if curves:
        curves_selection = filter(None, map(str.strip, curves.split(',')))
        curves_selection = list(dict.fromkeys(curves_selection))

    try:
        response = await bulk_io.get_statistics(ctx, record.id, bulk_uri.bulk_id, curves_selection)
    except BulkCurvesNotFound as e:
        raise BulkStatisticsHTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                          error_type=statistics_exceptions.RequestedCurvesError.public_error_type,
                                          message=str(e))
    except BulkRecordNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (statistics_exceptions.StatisticsNotFoundError,
            statistics_exceptions.RequestedCurvesError,
            statistics_exceptions.ComputationNotCompleteError) as e:
        raise BulkStatisticsHTTPException(status_code=status.HTTP_404_NOT_FOUND, error_type=e.public_error_type,
                                          message=str(e))
    return response


@router.post(
    '/{record_id}/versions/{version}/data/statistics',
    summary="Trigger computations of record's data statistics of record's data",
    description=f"""Trigger the computation of statistics on bulk data for 
    the record identified by the record_id at its last version   

    {api_unit_conversion_text}
    """,
    
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Statistics or record not found"},
        status.HTTP_409_CONFLICT: {"description": "Statistics computation already running or complete"},
        status.HTTP_200_OK: {"description": "Statistics computation started"},
    }
)
async def compute_bulk_statistics(
        request: Request,
        record_id: WellLogId,
        version: int,
        record: Record = Depends(fetch_record_dependency),
        bulk_io: BulkIO = Depends(get_bulk_io_read),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
        ctx: Context = Depends(get_ctx),
):
    try:
        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI') from e
    if not bulk_uri.is_valid():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='Record contains an invalid bulk URI')

    try:
        await bulk_io.post_statistics(ctx, record.id, bulk_uri.bulk_id, record.version)
    except statistics_exceptions.ComputationRunningError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
