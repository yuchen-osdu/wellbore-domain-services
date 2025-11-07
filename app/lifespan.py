import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.bulk_persistence import BulkIO
from app.injector.app_injector import AppInjector
from app.clients import StorageRecordServiceClient, SearchServiceClient
from app.conf import Config, check_environment
from app.helper import logger, traces_ot
from app.injector.main_injector import MainInjector

app_injector = AppInjector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_event()
    yield
    await shutdown_event()


def startup_event():
    service_name = Config.service_name.value
    logger.init_logger(service_name=service_name, config=Config)

    # check python version >=3.13
    assert sys.version_info.major == 3 and sys.version_info.minor >= 13, 'Python version required >=3.13'

    check_environment(Config)
    MainInjector().configure(app_injector)
    traces_ot.initialize_tracer(service_name=service_name, config=Config)


async def shutdown_event():
    # clients close
    storage_client = await app_injector.get(StorageRecordServiceClient)
    if storage_client is not None and hasattr(storage_client, 'api_client'):
        await storage_client.api_client.close()

    search_client = await app_injector.get(SearchServiceClient)
    if search_client is not None and hasattr(search_client, 'api_client'):
        await search_client.api_client.close()

    bulk_client = await app_injector.get(BulkIO)
    if bulk_client is not None:
        bulk_client.close()
