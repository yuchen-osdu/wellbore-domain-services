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

from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi

from app import __version__, __build_number__, __app_name__
from app.auth.auth import require_opendes_authorized_user
from app.conf import Config, check_environment
from app.errors.exception_handlers import add_exception_handlers
from app.extensions import discoverer

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
    markerset_ddms_v3)
from app.routers.trajectory import trajectory_ddms_v2
from app.routers.dipset import dipset_ddms_v2, dip_ddms_v2
from app.routers.logrecognition import log_recognition
from app.routers.search import search, fast_search
from app.routers.ddms_v3 import bulk_v3
from app.clients import StorageRecordServiceClient, SearchServiceClient
from app.utils import get_http_client_session, OpenApiHandler, get_wdms_temp_dir

base_app = FastAPI()

# The sub application which contains all the routers
wdms_app = FastAPI(title=__app_name__,
                   description='build ' + __build_number__,
                   version=__version__,
                   )

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


@base_app.on_event("startup")
async def startup_event():
    service_name = Config.service_name.value

    logger.init_logger(service_name=service_name)
    check_environment(Config)
    print('using temporary directory:', get_wdms_temp_dir())
    MainInjector().configure(app_injector)
    wdms_app.trace_exporter = traces.create_exporter(service_name=service_name)

    if Config.alpha_feature_enabled.value:
        enable_alpha_feature()

    add_extension_routers()


@base_app.on_event('shutdown')
async def shutdown_event():
    # clients close
    storage_client = await app_injector.get(StorageRecordServiceClient)
    if storage_client is not None:
        await storage_client.api_client.close()

    search_client = await app_injector.get(SearchServiceClient)
    if search_client is not None:
        await storage_client.api_client.close()

    await get_http_client_session().close()


DDMS_V2_PATH = '/ddms/v2'
DDMS_V3_PATH = '/ddms/v3'
ALPHA_APIS_PREFIX = '/alpha'


wdms_app.include_router(probes.router)
wdms_app.include_router(about.router, prefix=DDMS_V2_PATH)

ddms_v2_routes_groups = [
    (ddms_v2, "Wellbore DDMS"),
    (well_ddms_v2, "Well"),
    (wellbore_ddms_v2, "Wellbore"),
    (logset_ddms_v2, "Logset"),
    (trajectory_ddms_v2, "Trajectory"),
    (marker_ddms_v2, "Marker"),
    (log_ddms_v2, "Log"),
    (dipset_ddms_v2, "Dipset"),
    (dip_ddms_v2, "Dips"),
]
for ddms_v2_routes_group in ddms_v2_routes_groups:
    wdms_app.include_router(ddms_v2_routes_group[0].router,
                            prefix=DDMS_V2_PATH,
                            tags=[ddms_v2_routes_group[1]],
                            dependencies=[
                                Depends(require_opendes_authorized_user, use_cache=False),
                                Depends(require_data_partition_id, use_cache=False)
                            ])

ddms_v3_routes_groups = [
    (wellbore_ddms_v3, "Wellbore"),
    (well_ddms_v3, "Well"),
    (welllog_ddms_v3, "WellLog"),
    (wellbore_trajectory_ddms_v3, "Trajectory"),
    (markerset_ddms_v3, "Marker"),
]
for ddms_v3_routes_group in ddms_v3_routes_groups:
    wdms_app.include_router(ddms_v3_routes_group[0].router,
                            prefix=DDMS_V3_PATH,
                            tags=[ddms_v3_routes_group[1]],
                            dependencies=[
                                Depends(require_opendes_authorized_user, use_cache=False),
                                Depends(require_data_partition_id, use_cache=False)
                            ])

wdms_app.include_router(search.router, prefix='/ddms', tags=['search'], dependencies=[
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False)
])
wdms_app.include_router(fast_search.router, prefix='/ddms', tags=['fast-search'], dependencies=[
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False)])

wdms_app.include_router(log_recognition.router, prefix='/log-recognition', tags=['log-recognition'], dependencies=[
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False)])


dependencies = [Depends(require_data_partition_id, use_cache=False),
                Depends(require_opendes_authorized_user, use_cache=False)]


tags = ['ALPHA feature: bulk data chunking']

# welllog bulk v3 APIs
wdms_app.include_router(
    sessions.router,
    prefix=ALPHA_APIS_PREFIX + DDMS_V3_PATH + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
    tags=tags, dependencies=dependencies)
wdms_app.include_router(
    bulk_v3.router_bulk,
    prefix=ALPHA_APIS_PREFIX + DDMS_V3_PATH + welllog_ddms_v3.WELL_LOGS_API_BASE_PATH,
    tags=tags, dependencies=dependencies)

# wellbore trajectory bulk v3 APIs
wdms_app.include_router(
    sessions.router,
    prefix=ALPHA_APIS_PREFIX + DDMS_V3_PATH + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
    tags=tags, dependencies=dependencies)
wdms_app.include_router(
    bulk_v3.router_bulk,
    prefix=ALPHA_APIS_PREFIX + DDMS_V3_PATH + wellbore_trajectory_ddms_v3.WELLBORE_TRAJECTORIES_API_BASE_PATH,
    tags=tags, dependencies=dependencies)

# ------------- add alpha feature: ONLY MOUNTED IN DEV AND DA ENVs
def enable_alpha_feature():
    """ must be called to enable and activate alpha feature"""
    logger.get_logger().warning("Enabling alpha feature: chunking")

    # include alpha routers down below #


# order is last executed first
wdms_app.add_middleware(TracingMiddleware)
wdms_app.add_middleware(CreateBasicContextMiddleware, injector=app_injector)

# adding exception handling
add_exception_handlers(wdms_app)


# Load and add router extensions [alpha version]
def add_extension_routers():
    for router in discoverer.get_routers():
        add_extension_router(router)


def add_extension_router(router):
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
