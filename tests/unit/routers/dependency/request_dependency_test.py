import pytest

from fastapi import FastAPI, APIRouter, Depends
from httpx import AsyncClient, ASGITransport
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers.dependency.request_dependency import RequestDependencyBase, RequestDependencyMetaClass


class TestDependencyWithDefault(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
    default = "default_value"


class TestDependencyNoDefault(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
    pass


class AddRequestStateDependencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.dependencies = dict()
        return await call_next(request)


router = APIRouter()


@router.get('/route-a')
async def get_route_a(value=Depends(TestDependencyWithDefault())):
    return {"value": value}


@router.get('/route-b')
async def get_route_b(value=Depends(TestDependencyNoDefault())):
    return {"value": value}


BASE_URL = "http://local_app"

@pytest.fixture(scope="module")
def test_client():

    local_app = FastAPI()

    local_app.include_router(router, prefix='/path-1', dependencies=[
        Depends(TestDependencyWithDefault.with_value("1")),
        Depends(TestDependencyNoDefault.with_value(1))
    ])

    local_app.include_router(router, prefix='/path-2', dependencies=[
        Depends(TestDependencyWithDefault.with_value("2")),
        Depends(TestDependencyNoDefault.with_value(2))
    ])

    local_app.include_router(router, prefix='/path-default')
    local_app.add_middleware(AddRequestStateDependencyMiddleware)

    ac = AsyncClient(transport=ASGITransport(local_app), base_url=BASE_URL)
    yield ac


@pytest.mark.anyio
async def test_dependency_value_resolution(test_client):
    assert (await test_client.get(f'{BASE_URL}/path-1/route-a')).json()["value"] == "1"
    assert (await test_client.get(f'{BASE_URL}/path-1/route-b')).json()["value"] == 1

    assert (await test_client.get(f'{BASE_URL}/path-2/route-a')).json()["value"] == "2"
    assert (await test_client.get(f'{BASE_URL}/path-2/route-b')).json()["value"] == 2


@pytest.mark.anyio
async def test_dependency_default_value_resolution(test_client, anyio_backend):
    # WHEN default is defined
    assert (await test_client.get(f'{BASE_URL}/path-default/route-a')).json()["value"] == "default_value"

    # WHEN default is not defined, should raise
    with pytest.raises(RuntimeError):
        await test_client.get(f'{BASE_URL}/path-default/route-b')
