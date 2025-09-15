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

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.openapi.utils import get_openapi

from app import __app_name__, __build_number__, __version__
from app.auth.auth import require_opendes_authorized_user

# ---------- import Bulk persistence ----------------------------------
# ---------- import Core services clients ----------------------------------

# ----------
from app.conf import Config
from app.errors.exception_handlers import add_exception_handlers


# ---------- import tracing, logging, metrics ----------------------------------
# ---------- import DI ----------------------------------

# ---------- import middlewares ----------------------------------
from app.middleware import CreateBasicContextMiddleware, TracingMiddlewareOT
from app.middleware.basic_context_middleware import require_data_partition_id, ServerTimingHdrMiddleware
from app.middleware.openapi_middleware import OpenAPIMiddleware
from app.model.api_configuration import APIConfiguration, PPFGDatasetAPI, WellPressureTestRawMeasurementAPI
# ---------- import model ----------------------------------
from app.model.entity_utils import Entity

# ---------- import Routers ----------------------------------
from app.routers import about, probes, sessions
from app.routers.bulk import bulk_routes, statistics_routes
from app.routers.bulk.bulk_routes_dependencies import (
    set_log_bulk_id_access,
    set_osdu_bulk_id_access,
)
from app.routers.bulk.utils import (
    set_legacy_input_dataframe_check,
    set_trajectory_data_consistency_check,
    set_v3_input_dataframe_check,
    set_welllog_data_consistency_check,
    update_operation_ids,
    set_ppfgdataset_consistency_check,
    set_wellpressuretestrawmeasurement_consistency_check,
)
from app.routers.common_parameters import (
    response_401,
    response_403,
    response_500,
)
from app.routers.ddms_v2 import log_ddms_v2
from app.routers.ddms_v3 import (
    markerset_ddms_v3,
    well_ddms_v3,
    wellbore_ddms_v3,
    wellbore_trajectory_ddms_v3,
    welllog_ddms_v3,
    wellbore_interval_set_ddms_v3,
    welllog_acquisition_v3,
    generic_ddms_v3
)
from app.routers.dependency import (
    FetchRecordDependency,
    FetchRecordPartialDependency,
)
from app.routers.dipset import dip_ddms_v2, dipset_ddms_v2
from app.routers.log_recognition import log_recognition
from app.routers.record_utils import (
    fetch_record_dependency,
    fetch_record_partial_with_wdms_extension,
)
from app.utils import OpenApiHandler
from app.lifespan import lifespan, app_injector
from app.helper import metric


# create module logger
logger = logging.getLogger(__name__)

# The sub application which contains all the routers
wdms_app = FastAPI(root_path=Config.openapi_prefix.value,
                   title=__app_name__,
                   description='build ' + __build_number__,
                   version=__version__,
                   lifespan=lifespan)

# Add Prometheus metrics middleware before app startup for Azure
metric.init_metric(wdms_app, logger)

def custom_openapi(*args, **kwargs):
    if wdms_app.openapi_schema:
        return wdms_app.openapi_schema
    openapi_schema = get_openapi(
        title=wdms_app.title,
        version=wdms_app.version,
        description=wdms_app.description,
        routes=wdms_app.routes,
        servers=wdms_app.servers
    )

    routes_in_schemas = [route for route in wdms_app.routes if getattr(route, 'include_in_schema', True)]
    OpenApiHandler(openapi_schema, [getattr(route, 'operation_id', None) for route in routes_in_schemas])

    wdms_app.openapi_schema = openapi_schema
    return wdms_app.openapi_schema


wdms_app.openapi = custom_openapi


def hide_router_modules(modules):
    for mod in modules:
        for rte in mod.router.routes:
            rte.include_in_schema = False


def make_entity_type_dependency(entity_type: Entity, version: str):
    def _set_entity_type(request: Request):
        request.state.entity_type = entity_type
        request.state.version = version
    return _set_entity_type

def make_api_config(api_config: APIConfiguration):
    def set_api_config(request: Request):
        request.state.api_config = api_config
    return set_api_config




DDMS_V2_PATH = '/ddms/v2'
DDMS_V3_PATH = '/ddms/v3'
ALPHA_APIS_PREFIX = '/alpha'
basic_dependencies = [
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False),
]

wdms_app.include_router(probes.router)
wdms_app.include_router(about.router, tags=["Wellbore DDMS"], responses={**response_500})

# hidden from swagger but maintained for backward compatibility with /ddms/v2 APIs
wdms_app.include_router(about.router, prefix=DDMS_V2_PATH, tags=["Wellbore DDMS"], include_in_schema=False,
                        responses={**response_500})

ddms_v3_routes_groups_without_bulk = [
    (wellbore_ddms_v3, "Wellbore", Entity.WELLBORE),
    (well_ddms_v3, "Well", Entity.WELL),
    (markerset_ddms_v3, "Marker", Entity.MARKER),
    (wellbore_interval_set_ddms_v3, "Wellbore IntervalSet", Entity.WELLBOREINTERVALSET),
    (welllog_acquisition_v3, "WellLog Acquisition", Entity.WELLLOGACQUISITION)
]

ddms_v3_routes_groups_with_bulk = [
    (welllog_ddms_v3, "WellLog", Entity.WELL_LOG),
    (wellbore_trajectory_ddms_v3, "Trajectory v3", Entity.TRAJECTORY),
]

for v3_api, tag, entity_type in ddms_v3_routes_groups_without_bulk:
    wdms_app.include_router(v3_api.router,
                            prefix=DDMS_V3_PATH,
                            tags=[tag],
                            responses={**response_401, **response_403, **response_500},
                            dependencies=[*basic_dependencies, Depends(make_entity_type_dependency(entity_type, "V3"))])

v3_bulk_dependencies = [*basic_dependencies, Depends(set_v3_input_dataframe_check), Depends(set_osdu_bulk_id_access)]
for v3_api, tag, entity_type in ddms_v3_routes_groups_with_bulk:
    wdms_app.include_router(v3_api.router,
                            prefix=DDMS_V3_PATH,
                            tags=[tag],
                            responses={**response_401, **response_403, **response_500},
                            dependencies=[*v3_bulk_dependencies, Depends(make_entity_type_dependency(entity_type, "V3"))])


# POST and GET v3/welllog/session   (EXCLUDE  PATCH commit/abandon)
wdms_app.include_router(
    sessions.router,
    prefix=DDMS_V3_PATH + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
    tags=["WellLog"],
    dependencies=[
        *basic_dependencies,
        Depends(set_welllog_data_consistency_check),
        Depends(make_entity_type_dependency(Entity.WELL_LOG, "V3"))
    ],
    responses={**response_401, **response_403, **response_500})

# POST v3/welllogs/{record_id}/data
# POST v3/welllogs/{record_id}/sessions/{session_id}/data
# GET v3/welllogs/{record_id}/versions/{version}/data
# GET v3/welllogs/{record_id}/data
# PATCH v3/welllogs/{record_id}/sessions/{session_id}
wdms_app.include_router(
    bulk_routes.router,
    prefix=DDMS_V3_PATH + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
    tags=["WellLog"],
    dependencies=[
        *v3_bulk_dependencies,
        Depends(make_entity_type_dependency(Entity.WELL_LOG, "V3")),
        Depends(set_welllog_data_consistency_check),
        Depends(FetchRecordDependency.with_value(fetch_record_dependency)),
        Depends(FetchRecordPartialDependency.with_value(fetch_record_partial_with_wdms_extension))
    ],
    responses={**response_401, **response_403, **response_500})

# POST and GET v3/wellboretrajectories/session   (EXCLUDE  PATCH commit/abandon)
wdms_app.include_router(
    sessions.router,
    prefix=DDMS_V3_PATH + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
    tags=["Trajectory v3"],
    dependencies=[
        *basic_dependencies,
        Depends(set_trajectory_data_consistency_check),
        Depends(make_entity_type_dependency(Entity.TRAJECTORY, "V3")),
    ],
    responses={**response_401, **response_403, **response_500})

# POST v3/wellboretrajectories/{record_id}/data
# POST v3/wellboretrajectories/{record_id}/sessions/{session_id}/data
# GET v3/wellboretrajectories/{record_id}/versions/{version}/data
# GET v3/wellboretrajectories/{record_id}/data
# PATCH v3/{wellboretrajectories}/{record_id}/sessions/{session_id}
wdms_app.include_router(
    bulk_routes.router,
    prefix=DDMS_V3_PATH + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
    tags=["Trajectory v3"],
    dependencies=[
        *v3_bulk_dependencies,
        Depends(make_entity_type_dependency(Entity.TRAJECTORY, "V3")),
        Depends(set_trajectory_data_consistency_check),
        Depends(FetchRecordDependency.with_value(fetch_record_dependency)),
        Depends(FetchRecordPartialDependency.with_value(fetch_record_partial_with_wdms_extension))
    ],
    responses={**response_401, **response_403, **response_500})

# Statistics endpoints
v3_bulk_dependencies = [*basic_dependencies, Depends(set_v3_input_dataframe_check),
                        Depends(set_osdu_bulk_id_access)]
wdms_app.include_router(
    statistics_routes.router,
    prefix=DDMS_V3_PATH + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
    tags=["WellLog"],
    dependencies=[
        *basic_dependencies,
        Depends(make_entity_type_dependency(Entity.WELL_LOG, "V3")),
        Depends(set_osdu_bulk_id_access)
    ],
    responses={**response_401, **response_403, **response_500},
    include_in_schema=True)


# POST and GET v3/ppfgdataset/session   (EXCLUDE  PATCH commit/abandon)
wdms_app.include_router(
    sessions.router,
    prefix=DDMS_V3_PATH + PPFGDatasetAPI.entity_uri,
    tags=["PPFGDataset v3"],
    dependencies=[
        *basic_dependencies,
        Depends(set_ppfgdataset_consistency_check),
        Depends(make_entity_type_dependency(Entity.PPFGDATASET, "V3")),
    ],
    responses={**response_401, **response_403, **response_500})

# POST v3/ppfgdataset/{record_id}/data
# POST v3/ppfgdataset/{record_id}/sessions/{session_id}/data
# GET v3/ppfgdataset/{record_id}/versions/{version}/data
# GET v3/ppfgdataset/{record_id}/data
# PATCH v3/{ppfgdataset}/{record_id}/sessions/{session_id}
wdms_app.include_router(
    bulk_routes.router,
    prefix=DDMS_V3_PATH + PPFGDatasetAPI.entity_uri,
    tags=["PPFGDataset v3"],
    dependencies=[
        *v3_bulk_dependencies,
        Depends(make_entity_type_dependency(Entity.PPFGDATASET, "V3")),
        Depends(set_ppfgdataset_consistency_check),
        Depends(FetchRecordDependency.with_value(fetch_record_dependency)),
        Depends(FetchRecordPartialDependency.with_value(fetch_record_partial_with_wdms_extension))
    ],
    responses={**response_401, **response_403, **response_500})

# POST and GET v3/wellpressuretestrawmeasurement/session   (EXCLUDE  PATCH commit/abandon)
wdms_app.include_router(
    sessions.router,
    prefix=DDMS_V3_PATH + WellPressureTestRawMeasurementAPI.entity_uri,
    tags=[WellPressureTestRawMeasurementAPI.tag],
    dependencies=[
        *basic_dependencies,
        Depends(set_wellpressuretestrawmeasurement_consistency_check),
        Depends(make_entity_type_dependency(Entity.WELLPRESSURETESTRAWMEASUREMENT, "V3")),
    ],
    responses={**response_401, **response_403, **response_500})

# POST v3/wellpressuretestrawmeasurement/{record_id}/data
# POST v3/wellpressuretestrawmeasurement/{record_id}/sessions/{session_id}/data
# GET v3/wellpressuretestrawmeasurement/{record_id}/versions/{version}/data
# GET v3/wellpressuretestrawmeasurement/{record_id}/data
# PATCH v3/{wellpressuretestrawmeasurement}/{record_id}/sessions/{session_id}
wdms_app.include_router(
    bulk_routes.router,
    prefix=DDMS_V3_PATH + WellPressureTestRawMeasurementAPI.entity_uri,
    tags=[WellPressureTestRawMeasurementAPI.tag],
    dependencies=[
        *v3_bulk_dependencies,
        Depends(make_entity_type_dependency(Entity.WELLPRESSURETESTRAWMEASUREMENT, "V3")),
        Depends(set_wellpressuretestrawmeasurement_consistency_check),
        Depends(FetchRecordDependency.with_value(fetch_record_dependency)),
        Depends(FetchRecordPartialDependency.with_value(fetch_record_partial_with_wdms_extension))
    ],
    responses={**response_401, **response_403, **response_500})


# Expose the Following APIs
# POST v3/{entityName}
# GET v3/{entityName}/{record_id}
# GET v3/{entityName}/{record_id}/versions
# GET v3/{entityName}/{record_id}/versions/{version_id}
# DELETE v3/{entityName}/{record_id}
ddms_v3_routes_crud_api: list[APIConfiguration] = [
    PPFGDatasetAPI, WellPressureTestRawMeasurementAPI
]

for crud_api_config in ddms_v3_routes_crud_api:
    wdms_app.include_router(generic_ddms_v3.router,
                            prefix=DDMS_V3_PATH + crud_api_config.entity_uri,
                            tags=[crud_api_config.tag],
                            responses={**response_401, **response_403, **response_500},
                            dependencies=[*basic_dependencies, *v3_bulk_dependencies,
                                            Depends(make_entity_type_dependency(crud_api_config.entity, "V3")),
                                            Depends(make_api_config(crud_api_config))
                            ])

# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ------------------------------------------- Log recognition ---------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
wdms_app.include_router(log_recognition.router,
                        dependencies=[Depends(require_data_partition_id, use_cache=False),
                                      Depends(require_opendes_authorized_user, use_cache=False)],
                        responses={**response_401, **response_403, **response_500},)


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- Deprecated API set ---------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

ddms_v2_routes_groups = [
    (log_ddms_v2, "Log", Entity.LOG),
    (dipset_ddms_v2, "Dipset", Entity.DIPSET),
    (dip_ddms_v2, "Dips", Entity.DIP),
]
for v2_api, tag, entity_type in ddms_v2_routes_groups:
    wdms_app.include_router(v2_api.router,
                            deprecated=True,
                            prefix=DDMS_V2_PATH,
                            tags=[tag],
                            responses={**response_401, **response_403, **response_500},
                            dependencies=[*basic_dependencies, Depends(make_entity_type_dependency(entity_type, "V2"))])

# log bulk v2 APIs
wdms_app.include_router(
    sessions.router,
    deprecated=True,
    prefix=ALPHA_APIS_PREFIX + DDMS_V2_PATH + log_ddms_v2.LOGS_API_BASE_PATH,
    tags=["DEPRECATED"],
    responses={**response_401, **response_403, **response_500},
    dependencies=[*basic_dependencies, Depends(make_entity_type_dependency(Entity.LOG, "V2"))])

wdms_app.include_router(
    bulk_routes.router,
    deprecated=True,
    prefix=ALPHA_APIS_PREFIX + DDMS_V2_PATH + log_ddms_v2.LOGS_API_BASE_PATH,
    tags=["DEPRECATED"],
    responses={**response_401, **response_403, **response_500},
    dependencies=[*basic_dependencies,
                  Depends(set_legacy_input_dataframe_check),
                  Depends(set_log_bulk_id_access),
                  Depends(make_entity_type_dependency(Entity.LOG, "V2")),
                  Depends(FetchRecordDependency.with_value(fetch_record_dependency)),
                  # As V2 is deprecated, simply fetch the whole record in all cases
                  Depends(FetchRecordPartialDependency.with_value(fetch_record_dependency))
                  ])


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# -------------------------------------------- Middlewares ------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------


# The multiple instantiation of bulk_utils router create some duplicated operation_id
update_operation_ids(wdms_app)

if Config.swagger_full_url_enabled.value:
    wdms_app.add_middleware(OpenAPIMiddleware)

if Config.enable_header_server_timings.value:
    wdms_app.add_middleware(ServerTimingHdrMiddleware)

wdms_app.add_middleware(TracingMiddlewareOT, skip_for_path_suffix=[r.path for r in probes.router.routes])

# must be added last to be executed first, it's responsible to clean and create WDMS Context
wdms_app.add_middleware(CreateBasicContextMiddleware, config=Config, injector=app_injector)


# adding exception handling
add_exception_handlers(wdms_app)
