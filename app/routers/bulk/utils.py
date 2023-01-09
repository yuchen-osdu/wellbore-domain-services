import re
from fastapi import HTTPException, Request, status
from fastapi.routing import APIRoute
import pandas as pd
from pyarrow.lib import ArrowInvalid

from app.bulk_persistence import DaskBulkStorage, DataframeSerializerAsync, \
    MimeTypes, JSONOrient, \
    auto_cast_columns_to_string, columns_type_must_be_string, \
    no_validation, DataFrameValidationFunc
from app.clients.storage_service_client import get_storage_record_service
from app.context import get_ctx, Context
from app.utils import OpenApiHandler
from app.helper.traces import with_trace
from app.routers.bulk.bulk_uri_dependencies import BulkIdAccess

from app.consistency import NoConsistencyChecks, WelllogDataConsistencyChecks, TrajectoryDataConsistencyChecks


def update_operation_ids(wdms_app):
    """ Ensure all operation_id are uniques """

    def generate_unique_name(route: APIRoute) -> str:
        new_operation_id = list(route.methods)[0]
        new_operation_id += "_" + route.path
        new_operation_id = re.sub('[^a-zA-Z0-9\n\.]', '_', new_operation_id)
        new_operation_id = new_operation_id.lower()
        return new_operation_id

    operation_ids = set()
    for route in wdms_app.routes:
        if isinstance(route, APIRoute):
            if not route.operation_id or route.operation_id in operation_ids:
                new_operation_id = generate_unique_name(route)
                if route.operation_id in OpenApiHandler._handlers:
                    OpenApiHandler._handlers[new_operation_id] = OpenApiHandler._handlers[route.operation_id]
                route.operation_id = new_operation_id

            assert route.operation_id not in operation_ids
            operation_ids.add(route.operation_id)


async def set_v3_input_dataframe_check(request: Request):
    """
     Inject into request state (c.f. https://www.starlette.io/requests/#other-state)
     the check function. It aims for v3 bulk APIs
    """
    request.state.check_input_df_func = columns_type_must_be_string


async def set_legacy_input_dataframe_check(request: Request):
    """
    Inject into request state (c.f. https://www.starlette.io/requests/#other-state) the check function.
    For legacy routes, the check function is set according to content-type:
        - parquet: no backward compatibility required, same function that v3 bulk
        - json: backward compatibility required, the check function will cast column name type as string
     """
    content_type = request.headers.get('Content-Type')
    if MimeTypes.PARQUET.match(content_type):
        request.state.check_input_df_func = columns_type_must_be_string
    else:
        request.state.check_input_df_func = auto_cast_columns_to_string


def get_df_validation_func(request: Request) -> DataFrameValidationFunc:
    """
    Retrieve from request state (c.f. https://www.starlette.io/requests/#other-state) the injected input check function.
    This function is injected when mounting the bulk router into the fastApi app as router's 'dependencies'
    in module app/wdms_app.

    NOTE: attribute name 'check_input_df_func' which contains the function should be IDENTICAL
    that defined in above functions

    return: guarantee to return a not None dataframe validation function
    """
    if not getattr(request.state, 'check_input_df_func', None):
        return no_validation
    return request.state.check_input_df_func


def set_welllog_data_consistency_check(request: Request):
    request.state.data_consistency_checks = WelllogDataConsistencyChecks()


def set_trajectory_data_consistency_check(request: Request):
    request.state.data_consistency_checks = TrajectoryDataConsistencyChecks()


def get_data_consistency_checks(request: Request):
    if not getattr(request.state, 'data_consistency_checks', None):
        return NoConsistencyChecks()
    return request.state.data_consistency_checks


@with_trace("get_df_from_request")
async def get_df_from_request(request: Request) -> pd.DataFrame:
    """ Extract dataframe from request """

    ct = request.headers.get('Content-Type', '')
    if MimeTypes.PARQUET.match(ct):
        content = await request.body()  # request.stream()
        try:
            return await DataframeSerializerAsync().read_parquet(content)
        except (OSError, ArrowInvalid) as err:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f'{err}')  # TODO

    if MimeTypes.JSON.match(ct):
        content = await request.body()  # request.stream()
        try:
            return await DataframeSerializerAsync().read_json(content, JSONOrient.split)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail='invalid body')  # TODO

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f'Invalid content-type, "{ct}" is not supported')


@with_trace("with_dask_blob_storage")
async def with_dask_blob_storage() -> DaskBulkStorage:
    return await get_ctx().app_injector.get(DaskBulkStorage)


async def set_bulk_field_and_send_record(ctx: Context, bulk_id, record, bulk_uri_access: BulkIdAccess):
    bulk_uri_access.set_bulk_uri(record=record, bulk_id=bulk_id)

    # push new version on the storage
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(
        record=[record], data_partition_id=ctx.partition_id
    )
