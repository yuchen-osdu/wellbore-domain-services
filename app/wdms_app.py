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
import sys
from os import getpid
import asyncio
from time import sleep

from fastapi import FastAPI, Depends, Request
from fastapi.openapi.utils import get_openapi

from app import __version__, __build_number__, __app_name__
from app.auth.auth import require_opendes_authorized_user
from app.conf import Config, check_environment
from app.errors.exception_handlers import add_exception_handlers, create_custom_http_exception_handler
from app.helper.traces import TracingRoute
from app.model.entity_utils import Entity
from app.modules import discoverer

from app.helper import traces, logger
from app.injector.app_injector import AppInjector
from app.injector.main_injector import MainInjector
from app.middleware import CreateBasicContextMiddleware, TracingMiddleware
from app.middleware.basic_context_middleware import require_data_partition_id
from app.routers import probes, about, sessions
from app.routers.ddms_v2 import (
    ddms_v2,
    wellbore_ddms_v2,
    logset_ddms_v2,
    marker_ddms_v2,
    log_ddms_v2,
    well_ddms_v2
)
from app.routers.ddms_v3 import (
    wellbore_ddms_v3,
    well_ddms_v3,
    welllog_ddms_v3,
    wellbore_trajectory_ddms_v3,
    markerset_ddms_v3,
    delete_v3)
from app.routers.bulk import bulk_routes
from app.routers.trajectory import trajectory_ddms_v2
from app.routers.dipset import dipset_ddms_v2, dip_ddms_v2
from app.routers.search import search, fast_search, search_v3, fast_search_v3, search_v3_alpha
from app.clients import StorageRecordServiceClient, SearchServiceClient
from app.pool_executor import run_in_pool_executor
from app.utils import (
    get_http_client_session,
    OpenApiHandler,
    POOL_EXECUTOR_MAX_WORKER)
from app.bulk_persistence import DaskClient
from app.routers.bulk.utils import (
    update_operation_ids,
    set_v3_input_dataframe_check,
    set_legacy_input_dataframe_check,
    set_welllog_data_consistency_check,
    set_trajectory_data_consistency_check
)
from app.routers.bulk.bulk_uri_dependencies import (
    set_osdu_bulk_id_access,
    set_log_bulk_id_access
)

base_app = FastAPI()
base_app.router.route_class = TracingRoute

# The sub application which contains all the routers
wdms_app = FastAPI(title=__app_name__,
                   description='build ' + __build_number__,
                   version=__version__,
                   )
wdms_app.router.route_class = TracingRoute

app_injector = AppInjector()

base_app.mount(Config.openapi_prefix.value, wdms_app)


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


def executor_startup_task():
    """ This is a dummy task used to startup executors"""
    print(f"process {getpid()} started")
    sleep(0.2)  # to keep executor "busy"


def make_entity_type_dependency(entity_type: Entity, version: str):
    def _set_entity_type(request: Request):
        request.state.entity_type = entity_type
        request.state.version = version
    return _set_entity_type


@base_app.on_event("startup")
async def startup_event():
    service_name = Config.service_name.value

    logger.init_logger(service_name=service_name, config=Config)

    #check python version >=3.8
    assert sys.version_info.major == 3 and sys.version_info.minor >= 8, 'Python version required >=3.8'

    check_environment(Config)
    MainInjector().configure(app_injector)
    wdms_app.trace_exporter = traces.create_exporter(service_name=service_name, config=Config)

    # seems that the lock is not in the same event loop as requests
    # so we need to wait instead of just fire a task
    asyncio.create_task(DaskClient.create())
    create_custom_http_exception_handler(wdms_app, logger)
    # init executor pool
    logger.get_logger().info("Startup process pool executor")

    # force to adjust process count now instead of on first demand
    for _ in range(POOL_EXECUTOR_MAX_WORKER):
        asyncio.create_task(run_in_pool_executor(executor_startup_task))

    add_modules_routers()


@base_app.on_event('shutdown')
async def shutdown_event():
    # clients close
    storage_client = await app_injector.get(StorageRecordServiceClient)
    if storage_client is not None and hasattr(storage_client, 'api_client'):
        await storage_client.api_client.close()

    search_client = await app_injector.get(SearchServiceClient)
    if search_client is not None and hasattr(search_client, 'api_client'):
        await search_client.api_client.close()

    await get_http_client_session().close()
    await DaskClient.close()


DDMS_V2_PATH = '/ddms/v2'
DDMS_V3_PATH = '/ddms/v3'
ALPHA_APIS_PREFIX = '/alpha'
basic_dependencies = [
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False),
]

wdms_app.include_router(probes.router)
wdms_app.include_router(about.router, tags=["Wellbore DDMS"])

# hidden from swagger but maintained for backward compatibility with /ddms/v2 APIs
wdms_app.include_router(about.router, prefix=DDMS_V2_PATH, tags=["Wellbore DDMS"], include_in_schema=False)
wdms_app.include_router(ddms_v2.router, prefix=DDMS_V2_PATH, tags=["Wellbore DDMS"], include_in_schema=False)

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
                            prefix=DDMS_V2_PATH,
                            tags=[tag],
                            dependencies=[*basic_dependencies, Depends(make_entity_type_dependency(entity_type, "V2"))])

ddms_v3_routes_groups_without_bulk = [
    (wellbore_ddms_v3, "Wellbore", Entity.WELLBORE),
    (well_ddms_v3, "Well", Entity.WELL),
    (markerset_ddms_v3, "Marker", Entity.MARKER)
]

ddms_v3_routes_groups_with_bulk = [
    (welllog_ddms_v3, "WellLog", Entity.WELL_LOG),
    (wellbore_trajectory_ddms_v3, "Trajectory v3", Entity.TRAJECTORY)
]

for v3_api, tag, entity_type in ddms_v3_routes_groups_without_bulk:
    wdms_app.include_router(v3_api.router,
                            prefix=DDMS_V3_PATH,
                            tags=[tag],
                            dependencies=[*basic_dependencies, Depends(make_entity_type_dependency(entity_type, "V3"))])

v3_bulk_dependencies = [*basic_dependencies, Depends(set_v3_input_dataframe_check), Depends(set_osdu_bulk_id_access)]
for v3_api, tag, entity_type in ddms_v3_routes_groups_with_bulk:
    wdms_app.include_router(v3_api.router,
                            prefix=DDMS_V3_PATH,
                            tags=[tag],
                            dependencies=[*v3_bulk_dependencies, Depends(make_entity_type_dependency(entity_type, "V3"))])

wdms_app.include_router(search.router, prefix='/ddms', tags=['search'], dependencies=basic_dependencies)
wdms_app.include_router(fast_search.router, prefix='/ddms', tags=['fast-search'], dependencies=basic_dependencies)

wdms_app.include_router(search_v3.router, prefix=DDMS_V3_PATH, tags=['search v3'], dependencies=basic_dependencies)
wdms_app.include_router(fast_search_v3.router, prefix=DDMS_V3_PATH, tags=['fast-search v3'],
                        dependencies=basic_dependencies)
wdms_app.include_router(search_v3_alpha.router, prefix=ALPHA_APIS_PREFIX + DDMS_V3_PATH,
                        tags=['ALPHA feature: search v3'],
                        dependencies=basic_dependencies)

wdms_app.include_router(delete_v3.router, prefix=DDMS_V3_PATH, tags=["Delete records V3"], dependencies=basic_dependencies)

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
            Depends(make_entity_type_dependency(Entity.WELL_LOG, "V3"))
        ],
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
            Depends(set_welllog_data_consistency_check)
        ],
        include_in_schema=is_visible)

    # POST and GET v3/wellboretrajectories/session   (EXCLUDE  PATCH commit/abandon)
    wdms_app.include_router(
        sessions.router,
        prefix=bulk_prefix + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
        tags=bulk_tags if bulk_tags else ["Trajectory v3"],
        dependencies=[
            *basic_dependencies, 
            Depends(make_entity_type_dependency(Entity.TRAJECTORY, "V3")),
        ],
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
            Depends(set_trajectory_data_consistency_check)
        ],
        include_in_schema=is_visible)

# log bulk v2 APIs
wdms_app.include_router(
    sessions.router,
    prefix=ALPHA_APIS_PREFIX + DDMS_V2_PATH + log_ddms_v2.LOGS_API_BASE_PATH,
    tags=alpha_tags,
    dependencies=[*basic_dependencies, Depends(make_entity_type_dependency(Entity.LOG, "V2"))])
wdms_app.include_router(
    bulk_routes.router,
    prefix=ALPHA_APIS_PREFIX + DDMS_V2_PATH + log_ddms_v2.LOGS_API_BASE_PATH,
    tags=alpha_tags,
    dependencies=[*basic_dependencies, Depends(set_legacy_input_dataframe_check), Depends(set_log_bulk_id_access), Depends(make_entity_type_dependency(Entity.LOG, "V2"))])

# The multiple instantiation of bulk_utils router create some duplicated operation_id
update_operation_ids(wdms_app)


# order is last executed first
wdms_app.add_middleware(TracingMiddleware)

# must be added last to be executed first, it's responsible to clean and create WDMS Context
wdms_app.add_middleware(CreateBasicContextMiddleware, config=Config, injector=app_injector)


# adding exception handling
add_exception_handlers(wdms_app)


def remove_modules_routers():
    discoverer.reset_routers()


# Load and add router modules
def add_modules_routers():
    for router in discoverer.get_routers():
        add_modules_router(router)


def add_modules_router(router):
    log = logger.get_logger()
    name = router.prefix
    try:
        log.info(f'Adding router family `{name}`')
        wdms_app.include_router(router, dependencies=[Depends(require_data_partition_id, use_cache=False),
                                                      Depends(require_opendes_authorized_user, use_cache=False)])
        log.info(f'Done. `{name}` added')
    except ValueError as error:
        log.warning(f'Failed to add `{name}` router. {error}')
    except:
        log.warning(f'Failed to add `{name}` router. {sys.exc_info()[0]}')
