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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.model.model_chunking import GetDataParams, DataframeBasicDescribe

from app.context import Context, get_ctx

from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.common_parameters import read_bulk_accept_type
from app.routers.record_utils import fetch_record
from app.routers.bulk.bulk_uri_dependencies import get_bulk_id_access, BulkIdAccess
from app.routers.bulk.utils import (with_dask_blob_storage,
                                    DataFrameRender)

from app.bulk_persistence import JSONOrient
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.errors import BulkRecordNotFound
from app.bulk_persistence.mime_types import MimeTypes, MimeType
from app.bulk_persistence.statistics.bulk_statistics import BulkStatistics

from pydantic import BaseModel
from typing import Optional, List
from fastapi import Query

from helper.traces import TracingRoute

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


class BulkDataStatistics(BaseModel):
    columns: List[str]
    index: List[str]
    columns: List[str]
    data: List[List[float]]


api_description_text = """
If wanted curves is an array:
    - requests "ARRAY" retrieves all dimensions of the array
    - requests "ARRAY[M:N]", retrieves all dimensions between M and N.
"""


@router.get(
    '/{record_id}/data/statistics',
    summary="Returns statistics of record's data for selected curves",
    description=f"""
    Returns the statistics on bulk data identified by the record in its last version.

    {api_description_text}
    """,
    responses={
        404: {"description": "Statistics or record not found"},
        200: {"content": {
            MimeTypes.JSON.type: {},
            MimeTypes.PARQUET.type: {},
        }
        }
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
        accept_type: MimeType = Depends(read_bulk_accept_type)
):
    return await get_bulk_statistics_version(request=request,
                                             record_id=record_id,
                                             version=str(),
                                             curves=curves,
                                             ctx=ctx,
                                             dask_blob_storage=dask_blob_storage,
                                             bulk_uri_access=bulk_uri_access,
                                             accept_type=accept_type)


@router.get(
    '/{record_id}/versions/{version}/data/statistics',
    summary="Returns statistics of record's data for selected curves at requested version",
    description=f"""
    Returns the statistics on bulk data identified by the record and given version.

    {api_description_text}
    """,
    responses={
        404: {"description": "Statistics or record not found"},
        200: {"content": {
            MimeTypes.JSON.type: {},
            MimeTypes.PARQUET.type: {},
        }
        }
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
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
        accept_type: MimeType = Depends(read_bulk_accept_type)
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
        raise BulkRecordNotFound(record_id=record_id, bulk_id=None)

    columns = filter(None, map(str.strip, curves.split(',')))
    columns = list(dict.fromkeys(columns))

    stats_df = await BulkStatistics(dask_blob_storage).get_bulk_statistics(record.id, bulk_uri.bulk_id, columns)
    # stats_df = await dask_blob_storage.get_bulk_statistics(record.id, bulk_uri.bulk_id, columns)

    return await DataFrameRender.df_render(stats_df,
                                           GetDataParams(describe=False),
                                           accept_type,
                                           orient=JSONOrient.split,
                                           stat=None)


@router.post(
    '/{record_id}/data/statistics',
    summary="Trigger computations of record's data statistics of record's data",
    responses={
        404: {"description": "Statistics or record not found"},
        200: {"description": "Statistics computation started"},
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

    return await BulkStatistics(dask_blob_storage).compute_bulk_statistics(record.id, bulk_uri.bulk_id)
    # return await dask_blob_storage.compute_bulk_statistics(record.id, bulk_uri.bulk_id)