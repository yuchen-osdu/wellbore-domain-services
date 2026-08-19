from fastapi import Request

from app.bulk_persistence import (
    MimeTypes,
    auto_cast_columns_to_string,
    columns_type_must_be_string,
    no_validation,
    DataFrameValidationFunc,
)
from app.clients.storage_service_client import get_storage_record_service
from app.consistency.wellpressuretestrawmeasurement_consistency import WellPressureTestRawMeasurementConsistencyChecks
from app.context import Context
from app.routers.bulk.bulk_routes_dependencies import BulkIdAccess

from app.consistency import (
    NoConsistencyChecks,
    WelllogDataConsistencyChecks,
    TrajectoryDataConsistencyChecks,
    PPFGDatasetConsistencyChecks,
)


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
    content_type = request.headers.get("Content-Type")
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
    if not getattr(request.state, "check_input_df_func", None):
        return no_validation
    return request.state.check_input_df_func


def set_welllog_data_consistency_check(request: Request):
    request.state.data_consistency_checks = WelllogDataConsistencyChecks()


def set_trajectory_data_consistency_check(request: Request):
    request.state.data_consistency_checks = TrajectoryDataConsistencyChecks()

def set_ppfgdataset_consistency_check(request: Request):
    request.state.data_consistency_checks = PPFGDatasetConsistencyChecks()

def set_wellpressuretestrawmeasurement_consistency_check(request: Request):
    request.state.data_consistency_checks = WellPressureTestRawMeasurementConsistencyChecks()


def get_data_consistency_checks(request: Request):
    if not getattr(request.state, "data_consistency_checks", None):
        return NoConsistencyChecks()
    return request.state.data_consistency_checks


async def set_bulk_field_and_send_record(ctx: Context, bulk_id, record, bulk_uri_access: BulkIdAccess):
    bulk_uri_access.set_bulk_uri(record=record, bulk_id=bulk_id)

    # push new version on the storage
    storage_client = await get_storage_record_service(ctx)
    return await storage_client.create_or_update_records(record=[record], data_partition_id=ctx.partition_id)
