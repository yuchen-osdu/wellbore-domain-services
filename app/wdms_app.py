from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi import HTTPException

from app.routers import experiment, login, probes, parquet, about
from app.routers.ddms_v2 import ddms_v2, wellbore_ddms_v2, logset_ddms_v2, trajectory_ddms_v2, marker_ddms_v2, \
    log_ddms_v2, well_ddms_v2
from app.routers.logrecognition import log_recognition
from app.routers.storage import storage
from app.routers.entitlements import entitlements
from app.routers.search import search
from app.middleware import CreateBasicContextMiddleware, TracingMiddleware
from app.middleware.basic_context_middleware import require_data_partition_id, require_appkey
from app.injector.main_injector import MainInjector
from app.injector.app_injector import AppInjector
from app.auth.auth import require_opendes_authorized_user
from app.conf import Config, check_environment
from app.utils import get_http_client_session, OpenApiHandler, get_wdms_temp_dir

from app.helper import logger, traces
from app import __version__, __build_number__, __app_name__

from app.errors.validation_error import http422_error_handler

from odes_entitlements.exceptions import ApiException as OSDUEntitlementsException
from odes_search.exceptions import ApiException as OSDUSearchException
from odes_storage.exceptions import ApiException as OSDUStorageException

from app.errors.client_error import (
    http_search_error_handler,
    http_storage_error_handler,
    http_entitlements_error_handler
)

from app.errors.unhandled_error import unhandled_error_handler

ddms_logger = logger.init_logger()

wdms_app = FastAPI(title=__app_name__,
                   description='build ' + __build_number__,
                   version=__version__,

                   # https://fastapi.tiangolo.com/advanced/sub-applications-proxy/
                   # when deployed, it may be behind a proxy such as istio, with path being rewritten.
                   root_path=Config.openapi_prefix.value,
                   )

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

# These modules are only needed for development purposes
# they are enabled but the corresponding routers will only appear
# if the OS_WELLBORE_DDMS_SHOW_OPTIONAL_ROUTES env var is true
optional_modules = [storage, entitlements, search, parquet]


def hide_router_modules(modules):
    for mod in modules:
        for rte in mod.router.routes:
            rte.include_in_schema = False


# Check the OS_WELLBORE_DDMS_SHOW_OPTIONAL_ROUTES env var now
# at startup event routes are already displayed
if not Config.optional_routes.value:
    hide_router_modules(optional_modules)


@wdms_app.on_event("startup")
async def startup_event():
    check_environment(Config)
    print('using temporary directory:', get_wdms_temp_dir())
    MainInjector().configure(app_injector)
    wdms_app.trace_exporter = traces.create_exporter(service_name='os-wellbore-ddms')


@wdms_app.on_event('shutdown')
async def shutdown_event():
    await get_http_client_session().close()


wdms_app.include_router(login.router)
wdms_app.include_router(probes.router)
wdms_app.include_router(about.router)

ddms_v2_routes_groups = [
    (ddms_v2, "Wellbore DDMS"),
    (well_ddms_v2, "Well"),
    (wellbore_ddms_v2, "Wellbore"),
    (logset_ddms_v2, "Logset"),
    (trajectory_ddms_v2, "Trajectory"),
    (marker_ddms_v2, "Marker"),
    (log_ddms_v2, "Log"),
]
for ddms_v2_routes_group in ddms_v2_routes_groups:
    wdms_app.include_router(ddms_v2_routes_group[0].router,
                            prefix='/ddms/v2',
                            tags=[ddms_v2_routes_group[1]],
                            dependencies=[
                                Depends(require_opendes_authorized_user, use_cache=False),
                                Depends(require_data_partition_id, use_cache=False)
                            ])

wdms_app.include_router(storage.router, prefix='/ddms', tags=['storage'], dependencies=[
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False),
    Depends(require_appkey, use_cache=False)
])

wdms_app.include_router(entitlements.router, prefix='/ddms', tags=['entitlements'], dependencies=[
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False),
    Depends(require_appkey, use_cache=False)
])

wdms_app.include_router(search.router, prefix='/ddms', tags=['search'], dependencies=[
    Depends(require_data_partition_id, use_cache=False),
    Depends(require_opendes_authorized_user, use_cache=False),
    Depends(require_appkey, use_cache=False)
])
# wdms_app.include_router(experiment.router, prefix='/experiment', tags=['experiment'])
wdms_app.include_router(parquet.router, prefix='/parquet', tags=['parquet'])

wdms_app.include_router(log_recognition.router, prefix='/log-recognition', tags=['log-recognition'])

# order is last executed first
wdms_app.add_middleware(CreateBasicContextMiddleware, injector=app_injector, app_logger=ddms_logger)
wdms_app.add_middleware(TracingMiddleware)

# adding exception handling
wdms_app.add_exception_handler(RequestValidationError, http422_error_handler)
wdms_app.add_exception_handler(OSDUSearchException, http_search_error_handler)
wdms_app.add_exception_handler(OSDUStorageException, http_storage_error_handler)
wdms_app.add_exception_handler(OSDUEntitlementsException, http_entitlements_error_handler)
wdms_app.add_exception_handler(Exception, unhandled_error_handler)
