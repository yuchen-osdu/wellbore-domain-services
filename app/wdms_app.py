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
import sys
from functools import partial
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.openapi.utils import get_openapi

from app import __app_name__, __build_number__, __version__
from app.auth.auth import require_opendes_authorized_user

# ---------- import Bulk persistence ----------------------------------
from app.bulk_persistence import (
    BulkPersistenceConfig,
    dask_client,
    set_config_getter,
)
# ---------- import Core services clients ----------------------------------
from app.clients import SearchServiceClient, StorageRecordServiceClient

# ----------
from app.conf import Config, check_environment
from app.errors.exception_handlers import add_exception_handlers


# ---------- import tracing, logging, metrics ----------------------------------
from app.helper import logger, metric, traces
from app.helper.traces import TracingRoute
# ---------- import DI ----------------------------------
from app.injector.app_injector import AppInjector
from app.injector.main_injector import MainInjector
# ---------- import middlewares ----------------------------------
from app.middleware import CreateBasicContextMiddleware, TracingMiddleware
from app.middleware.basic_context_middleware import require_data_partition_id, ServerTimingHdrMiddleware
from app.middleware.openapi_middleware import OpenAPIMiddleware
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
)
from app.routers.common_parameters import (
    response_401,
    response_403,
    response_500,
)
from app.routers.ddms_v2 import (
    ddms_v2,
    log_ddms_v2,
    logset_ddms_v2,
    marker_ddms_v2,
    well_ddms_v2,
    wellbore_ddms_v2,
)
from app.routers.ddms_v3 import (
    markerset_ddms_v3,
    well_ddms_v3,
    wellbore_ddms_v3,
    wellbore_trajectory_ddms_v3,
    welllog_ddms_v3,
    wellbore_interval_set_ddms_v3,
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
from app.routers.search import search_v3, search_v3_alpha
from app.routers.trajectory import trajectory_ddms_v2
from app.utils import OpenApiHandler, get_http_client_session


# The sub application which contains all the routers
wdms_app = FastAPI(title=__app_name__,
                   description='build ' + __build_number__,
                   version=__version__,
                   )
wdms_app.router.route_class = TracingRoute

app_injector = AppInjector()

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


def _get_bulk_worker_host() -> Optional[str]:
    return Config.service_host_wdms_worker.value


@wdms_app.on_event("startup")
async def startup_event():
    service_name = Config.service_name.value

    logger.init_logger(service_name=service_name, config=Config)

    #check python version >=3.11
    assert sys.version_info.major == 3 and sys.version_info.minor >= 11, 'Python version required >=3.11'

    check_environment(Config)
    # build bulk persistence specific configuration

    # figure out bulk persistence backend: Dask or worker service
    worker_service_host = _get_bulk_worker_host()
    is_dask_backend = not bool(worker_service_host)

    bulk_config = BulkPersistenceConfig(
        min_worker_memory=Config.min_worker_memory.value,
        dask_data_ipc=Config.dask_data_ipc.value,
        service_name=Config.service_name.value,
        dask_enabled_on_read=is_dask_backend,
        dask_enabled_on_write=is_dask_backend,
        bulk_worker_host=worker_service_host
    )
    wdms_app.state.bulk_config = bulk_config
    set_config_getter(lambda: wdms_app.state.bulk_config)

    MainInjector().configure(app_injector)
    wdms_app.trace_exporter = traces.create_exporter(service_name=service_name, config=Config)

    app_injector.register(dask_client.DaskDistributedClient, partial(dask_client.create, bulk_config))
    asyncio.create_task(dask_client.create(bulk_config))

    metric.init_metric(wdms_app)


@wdms_app.on_event('shutdown')
async def shutdown_event():
    # clients close
    storage_client = await app_injector.get(StorageRecordServiceClient)
    if storage_client is not None and hasattr(storage_client, 'api_client'):
        await storage_client.api_client.close()

    search_client = await app_injector.get(SearchServiceClient)
    if search_client is not None and hasattr(search_client, 'api_client'):
        await search_client.api_client.close()

    await get_http_client_session().close()
    await dask_client.close()


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
wdms_app.include_router(ddms_v2.router, prefix=DDMS_V2_PATH, tags=["Wellbore DDMS"], include_in_schema=False,
                        responses={**response_401, **response_403, **response_500})


ddms_v3_routes_groups_without_bulk = [
    (wellbore_ddms_v3, "Wellbore", Entity.WELLBORE),
    (well_ddms_v3, "Well", Entity.WELL),
    (markerset_ddms_v3, "Marker", Entity.MARKER),
    (wellbore_interval_set_ddms_v3, "Wellbore IntervalSet", Entity.WELLBOREINTERVALSET)
]

ddms_v3_routes_groups_with_bulk = [
    (welllog_ddms_v3, "WellLog", Entity.WELL_LOG),
    (wellbore_trajectory_ddms_v3, "Trajectory v3", Entity.TRAJECTORY)
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

wdms_app.include_router(
    search_v3.router,
    prefix=DDMS_V3_PATH,
    deprecated=True,
    tags=["DEPRECATED"],
    dependencies=basic_dependencies,
    responses={**response_401, **response_403, **response_500}
)

wdms_app.include_router(
    search_v3_alpha.router,
    prefix=ALPHA_APIS_PREFIX + DDMS_V3_PATH,
    deprecated=True,
    tags=["DEPRECATED"],
    dependencies=basic_dependencies,
    responses={**response_401, **response_403, **response_500}
)


alpha_tags = ['ALPHA feature: bulk data chunking']

for bulk_prefix, bulk_tags, is_visible in [(ALPHA_APIS_PREFIX + DDMS_V3_PATH, alpha_tags, False),
                                           (DDMS_V3_PATH, [], True)
                                           ]:

    # POST and GET v3/welllog/session   (EXCLUDE  PATCH commit/abandon)
    wdms_app.include_router(
        sessions.router,
        prefix=bulk_prefix + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
        tags=bulk_tags if bulk_tags else ["WellLog"],
        dependencies=[
            *basic_dependencies,
            Depends(set_welllog_data_consistency_check),
            Depends(make_entity_type_dependency(Entity.WELL_LOG, "V3"))
        ],
        responses={**response_401, **response_403, **response_500},
        include_in_schema=is_visible)

    # POST v3/welllogs/{record_id}/data
    # POST v3/welllogs/{record_id}/sessions/{session_id}/data
    # GET v3/welllogs/{record_id}/versions/{version}/data
    # GET v3/welllogs/{record_id}/data
    # PATCH v3/welllogs/{record_id}/sessions/{session_id}
    wdms_app.include_router(
        bulk_routes.router,
        prefix=bulk_prefix + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
        tags=bulk_tags if bulk_tags else ["WellLog"],
        dependencies=[
            *v3_bulk_dependencies,
            Depends(make_entity_type_dependency(Entity.WELL_LOG, "V3")),
            Depends(set_welllog_data_consistency_check),
            Depends(FetchRecordDependency.with_value(fetch_record_dependency)),
            Depends(FetchRecordPartialDependency.with_value(fetch_record_partial_with_wdms_extension))
        ],
        responses={**response_401, **response_403, **response_500},
        include_in_schema=is_visible)

    # POST and GET v3/wellboretrajectories/session   (EXCLUDE  PATCH commit/abandon)
    wdms_app.include_router(
        sessions.router,
        prefix=bulk_prefix + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
        tags=bulk_tags if bulk_tags else ["Trajectory v3"],
        dependencies=[
            *basic_dependencies,
            Depends(set_trajectory_data_consistency_check),
            Depends(make_entity_type_dependency(Entity.TRAJECTORY, "V3")),
        ],
        responses={**response_401, **response_403, **response_500},
        include_in_schema=is_visible)

    # POST v3/wellboretrajectories/{record_id}/data
    # POST v3/wellboretrajectories/{record_id}/sessions/{session_id}/data
    # GET v3/wellboretrajectories/{record_id}/versions/{version}/data
    # GET v3/wellboretrajectories/{record_id}/data
    # PATCH v3/{wellboretrajectories}/{record_id}/sessions/{session_id}
    wdms_app.include_router(
        bulk_routes.router,
        prefix=bulk_prefix + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
        tags=bulk_tags if bulk_tags else ["Trajectory v3"],
        dependencies=[
            *v3_bulk_dependencies,
            Depends(make_entity_type_dependency(Entity.TRAJECTORY, "V3")),
            Depends(set_trajectory_data_consistency_check),
            Depends(FetchRecordDependency.with_value(fetch_record_dependency)),
            Depends(FetchRecordPartialDependency.with_value(fetch_record_partial_with_wdms_extension))
        ],
        responses={**response_401, **response_403, **response_500},
        include_in_schema=is_visible)

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
    (well_ddms_v2, "Well", Entity.WELL),
    (wellbore_ddms_v2, "Wellbore", Entity.WELLBORE),
    (logset_ddms_v2, "Logset", Entity.LOGSET),
    (trajectory_ddms_v2, "Trajectory", Entity.TRAJECTORY),
    (marker_ddms_v2, "Marker", Entity.MARKER),
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

# order is last executed first
wdms_app.add_middleware(TracingMiddleware, skip_for_path_suffix=[r.path for r in probes.router.routes])

# must be added last to be executed first, it's responsible to clean and create WDMS Context
wdms_app.add_middleware(CreateBasicContextMiddleware, config=Config, injector=app_injector)


# adding exception handling
add_exception_handlers(wdms_app)
