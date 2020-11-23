from fastapi import APIRouter, Depends, Header
import starlette.status as status
from starlette.responses import Response

from app.clients.storage_service_client import get_storage_record_service
from odes_storage.models import *
from app.model.model_curated import *
from app.utils import Context, get_ctx

router = APIRouter()


@router.get('/trajectories/{trajectoryid}',
            response_model=trajectory,
            summary="Get the trajectory using wks:trajectory:1.0.5 schema",
            description="""Get the Trajectory object using its **id**""",
            operation_id="get_trajectory",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Trajectory not found"}})
async def get_trajectory(
        trajectoryid: str,
        ctx: Context = Depends(get_ctx)
) -> trajectory:
    storage_service = await get_storage_record_service(ctx)
    trajectorydict = await storage_service.get_record(id=trajectoryid, data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:trajectory:1.0.5)
    return trajectory(**trajectorydict.dict())


@router.delete('/trajectories/{trajectoryid}',
               summary="Delete the Trajectory. The API performs a logical deletion of the given record",
               operation_id="del_trajectory",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={
                   status.HTTP_404_NOT_FOUND: {"description": "Trajectory not found"},
                   status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
               })
async def del_trajectory(
        trajectoryid: str,
        recursive: bool = Header(False),
        ctx: Context = Depends(get_ctx)):
    storage_service = await get_storage_record_service(ctx)
    await storage_service.delete_record(id=trajectoryid, data_partition_id=ctx.partition_id)


@router.get('/trajectories/{trajectoryid}/versions',
            response_model=RecordVersions,
            summary="Get all versions of the trajectory",
            operation_id="get_trajectory_versions",
            responses={status.HTTP_404_NOT_FOUND: {"description": "Trajectory not found"}})
async def get_trajectory_versions(
        trajectoryid: str,
        ctx: Context = Depends(get_ctx)
) -> RecordVersions:
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.get_all_record_versions(id=trajectoryid, data_partition_id=ctx.partition_id)


@router.get('/trajectories/{trajectoryid}/versions/{version}',
            response_model=trajectory,
            summary="Get the given version of trajectory using wks:trajectory:1.0.5 schema",
            operation_id="get_trajectory_version",
            responses={status.HTTP_404_NOT_FOUND: {"description": "trajectory not found"}})
async def get_trajectory_version(
        trajectoryid: str,
        version: int,
        ctx: Context = Depends(get_ctx)
) -> trajectory:
    storage_service = await get_storage_record_service(ctx)
    result_trajectory = await storage_service.get_record_version(id=trajectoryid,
                                                                 version=version,
                                                                 data_partition_id=ctx.partition_id)
    # TODO add a check on the kind (*:wks:logSet:1.0.5)
    return trajectory(**result_trajectory.dict())


@router.put('/trajectories',
            response_model=CreateUpdateRecordsResponse,
            summary="Create or update the trajectories using wks:trajectory:1.0.5 schema",
            operation_id="put_trajectory",
            responses={
                status.HTTP_400_BAD_REQUEST: {"description": "Missing mandatory parameter or unknown parameter"}
            })
async def put_trajectory(
        trajectories: List[trajectory],
        ctx: Context = Depends(get_ctx)
) -> CreateUpdateRecordsResponse:
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.create_or_update_records(record=trajectories,
                                                          data_partition_id=ctx.partition_id)

