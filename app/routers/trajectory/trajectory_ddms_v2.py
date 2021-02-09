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

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from starlette import status
from starlette.responses import Response
from pandas import DataFrame

from odes_storage.models import CreateUpdateRecordsResponse, RecordVersions

from app.clients.storage_service_client import get_storage_record_service
from app.model.model_curated import (
    trajectory as Trajectory,
    trajectorychannel as TrajectoryChannel,
)
from app.model.model_utils import from_record, to_record
from app.routers.common_parameters import json_orient_parameter
from app.routers.trajectory.persistence import Persistence
from app.bulk_persistence import DataframeSerializer, JSONOrient, MimeTypes

from app.utils import Context, OpenApiHandler, OpenApiResponse, get_ctx

router = APIRouter()

TrajectoryId = str


async def get_persistence() -> Persistence:
    return Persistence()


async def get_trajectory_record(ctx, trajectoryid: TrajectoryId) -> Trajectory:
    storage_client = await get_storage_record_service(ctx)
    return from_record(
        Trajectory,
        await storage_client.get_record(
            id=trajectoryid, data_partition_id=ctx.partition_id
        ),
    )


@router.get(
    "/trajectories/{trajectoryid}",
    response_model=Trajectory,
    summary="Get the trajectory using wks:trajectory:1.0.5 schema",
    description="""Get the Trajectory object using its **id**""",
    operation_id="get_trajectory",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Trajectory not found"}
    },
)
async def get_trajectory(
    trajectoryid: TrajectoryId, ctx: Context = Depends(get_ctx)
) -> Trajectory:
    # TODO add a check on the kind (*:wks:Trajectory:1.0.5)
    return await get_trajectory_record(ctx, trajectoryid)


@router.delete(
    "/trajectories/{trajectoryid}",
    summary="Delete the Trajectory. The API performs a logical deletion of the given record",
    operation_id="del_trajectory",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Trajectory not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Record deleted successfully"
        },
    },
)
async def del_trajectory(
    trajectoryid: TrajectoryId,
    ctx: Context = Depends(get_ctx),
):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_record(
        id=trajectoryid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/trajectories/{trajectoryid}/versions",
    response_model=RecordVersions,
    summary="Get all versions of the Trajectory",
    operation_id="get_trajectory_versions",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Trajectory not found"}
    },
)
async def get_trajectory_versions(
    trajectoryid: TrajectoryId, ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.get_all_record_versions(
        id=trajectoryid, data_partition_id=ctx.partition_id
    )


@router.get(
    "/trajectories/{trajectoryid}/versions/{version}",
    response_model=Trajectory,
    summary="Get the given version of Trajectory using wks:Trajectory:1.0.5 schema",
    operation_id="get_trajectory_version",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Trajectory not found"}
    },
)
async def get_trajectory_version(
    trajectoryid: TrajectoryId, version: int, ctx: Context = Depends(get_ctx)
) -> Trajectory:
    storage_client = await get_storage_record_service(ctx)
    trajectory_record = await storage_client.get_record_version(
        id=trajectoryid, version=version, data_partition_id=ctx.partition_id
    )
    return from_record(Trajectory, trajectory_record)


@router.post(
    "/trajectories",
    response_model=CreateUpdateRecordsResponse,
    summary="Create or update the trajectories using wks:Trajectory:1.0.5 schema",
    operation_id="post_trajectory",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing mandatory parameter or unknown parameter"
        }
    },
)
async def post_trajectory(
    trajectories: List[Trajectory], ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:

    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[to_record(tr) for tr in trajectories],
        data_partition_id=ctx.partition_id,
    )


_trajectory_dataframe_example = DataFrame([
    [0, 1001, 2001],
    [0.5, 1002, 2002],
    [1, 1003, 2003],
    [1.5, 1004, 2004],
    [2, 1005, 2005]],
    columns=['MD', 'X', 'Y']
)



# manually setup doc as we wanted to tweaked the classic mechanism in order to best perf as we can
@OpenApiHandler.set(
    operation_id="post_traj_data",
    request_body={
        'description':
            'Write trajectory bulk data. Each column corresponds to a channel.'
            '\nIt uses [Pandas.Dataframe json format]'
            '(https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html)' +
            '.\n Here\'re examples for data with {} rows and {} channels ({}) with different _orient_: '.format(
                _trajectory_dataframe_example.shape[0],
                _trajectory_dataframe_example.shape[1],
                ', '.join(_trajectory_dataframe_example.columns.tolist())) +
            ''.join([f'\n* {o.value}: <br/>`{DataframeSerializer.to_json(_trajectory_dataframe_example, o)}`<br/>&nbsp;'
                     for o in JSONOrient if o != JSONOrient.values]),
        # put examples here because of bug in swagger UI to properly render multiple examples
        "required": True,
        "content": {
            MimeTypes.JSON.type: {
                "schema": {
                    # swagger UI bug, so single example here
                    "example": DataframeSerializer.to_json(
                        _trajectory_dataframe_example,
                        JSONOrient.split
                    ),
                    "oneOf": [
                        DataframeSerializer.get_schema(o) for o in JSONOrient
                    ],
                }
            }
        },
    },
)
@router.post(
    "/trajectories/{trajectoryid}/data",
    summary="Writes the specified data to the trajectory (atomic).",
    description="Overwrite if exists",
    operation_id="post_traj_data",
    response_model=CreateUpdateRecordsResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "trajectory not found"},
        status.HTTP_200_OK: {},
    },
)
async def post_traj_data(
    request: Request,
    trajectoryid: TrajectoryId,
    orient: str = Depends(json_orient_parameter),
    ctx: Context = Depends(get_ctx),
    persistence: Persistence = Depends(get_persistence)) -> CreateUpdateRecordsResponse:

    content = await request.body()  # request.stream()
    df = DataframeSerializer.read_json(content, orient)

    record = await get_trajectory_record(ctx, trajectoryid)

    record.data.bulkURI = await persistence.write_bulk(ctx, df)

    # update record's channels
    if not record.data.channels:
        record.data.channels = []

    channels = {c.name: c for c in record.data.channels}

    record.data.channels = []
    for name in df.columns:
        channel = channels.get(name, TrajectoryChannel(name=name))
        channel.bulkURI = record.data.bulkURI + ":" + name
        record.data.channels.append(channel)

    # Update record
    storage_client = await get_storage_record_service(ctx)
    await storage_client.create_or_update_records(
        data_partition_id=ctx.partition_id, record=[record]
    )

    return record


@OpenApiHandler.set(
    operation_id="get_traj_data",
    responses=[
        OpenApiResponse(
            status=status.HTTP_200_OK,
            description=
            'Get trajectory data of the given channels.'
            '\nIt uses [Pandas.Dataframe json format]'
            '(https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html)' +
            '.\n Here\'re examples for data with {} rows for channels {} with different _orient_: '.format(
                _trajectory_dataframe_example.shape[0],
                ', '.join(_trajectory_dataframe_example.columns.tolist())) +
            ''.join([f'\n* {o.value}:  <br/>`{DataframeSerializer.to_json(_trajectory_dataframe_example, o)}`<br/>&nbsp;'
                     for o in JSONOrient]),
            name="GetLogDataResponse",
            example=DataframeSerializer.to_json(_trajectory_dataframe_example, JSONOrient.split),
            schema={
                "oneOf": [DataframeSerializer.get_schema(o) for o in JSONOrient]
            },
        )
    ],
)
@router.get(
    "/trajectories/{trajectoryid}/data",
    summary="Returns all data within the specified filters. Strongly consistent.",
    description="return full bulk data",
    operation_id="get_traj_data",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "trajectory not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "unknown channels"},
    },
)
async def get_traj_data(
    trajectoryid: TrajectoryId,
    orient: str = Depends(json_orient_parameter),
    channels: Optional[List[str]] = Query(
        None, description="List of channels to get. If not provided, return all channels."
    ),
    ctx: Context = Depends(get_ctx),
    persistence: Persistence = Depends(get_persistence),
):
    record = await get_trajectory_record(ctx, trajectoryid)

    df = await persistence.read_bulk(ctx, record, channels)
    content = DataframeSerializer.to_json(df, orient=orient)
    return Response(content=content, media_type=MimeTypes.JSON.type)
