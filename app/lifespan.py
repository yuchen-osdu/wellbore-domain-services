import asyncio
import sys
from contextlib import asynccontextmanager
from functools import partial
from typing import Optional

from fastapi import FastAPI

from app.injector.app_injector import AppInjector
from app.bulk_persistence import dask_client, BulkPersistenceConfig, set_config_getter
from app.clients import StorageRecordServiceClient, SearchServiceClient
from app.conf import Config, check_environment
from app.helper import logger, traces_ot, metric
from app.injector.main_injector import MainInjector
from app.utils import get_http_client_session

app_injector = AppInjector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_event(app)
    yield
    await shutdown_event()


def startup_event(app: FastAPI):
    service_name = Config.service_name.value
    logger.init_logger(service_name=service_name, config=Config)

    # check python version >=3.13
    assert sys.version_info.major == 3 and sys.version_info.minor >= 13, 'Python version required >=3.13'

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
    app.state.bulk_config = bulk_config
    set_config_getter(lambda: app.state.bulk_config)

    MainInjector().configure(app_injector)
    traces_ot.initialize_tracer(service_name=service_name, config=Config)

    app_injector.register(dask_client.DaskDistributedClient, partial(dask_client.create, bulk_config))
    asyncio.create_task(dask_client.create(bulk_config))

    metric.init_metric(app)


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

def _get_bulk_worker_host() -> Optional[str]:
    return Config.service_host_wdms_worker.value
