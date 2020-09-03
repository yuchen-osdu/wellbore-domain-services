from fastapi import APIRouter
from osdu_gcp.storage.blob_storage_gcp import GCloudAioStorage
from app.storage.tenant_provider import *
from app.utils import get_http_client_session
from app.utils import Context
from starlette.requests import Request

router = APIRouter()

# The following are only exploratory stuff and are not meant to go prod


@router.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}


class TestingInj:
    def __init__(self, v: str):
        self.v = v

    def get(self):
        return self.v


def create_builder(v: str):
    async def actual_builder():
        return TestingInj(v)
    return actual_builder


@router.get("/test_in/{value}")
async def testing_in(request: Request, value: str):
    injector = Context.from_request(request).app_injector
    injector.register(TestingInj, create_builder(value))
    return 'ok'


@router.get("/test_out")
async def testing_out(request: Request):
    injector = Context.from_request(request).app_injector
    obj: TestingInj = await injector.get(TestingInj)
    return {"value": obj.get()}


@router.get("/storage/download/{name}")
async def download_from_storage(name: str):
    tenant = await resolve_tenant('common')
    client = GCloudAioStorage(get_http_client_session(), service_account_file=tenant.credentials)
    return await client.download(tenant.project_id, tenant.bucket_name, name)


# TODO reading file is blocking here, it seems there's no full way do really do into async, may be looking to aiofile
# or aiofiles package (the second one is using threadpool, the one provide a real async on POSIX system) but benchmark
# shows bad performances: it seems better to run sync in an executor
@router.get("/storage/upload/{name}")
async def upload_to_storage(request: Request, name: str):
    tenant = await resolve_tenant('common')
    client = GCloudAioStorage(get_http_client_session(), service_account_file=tenant.credentials)

    with open(name) as f:
        return await client.upload(tenant.project_id, tenant.bucket_name, name, f.read())
