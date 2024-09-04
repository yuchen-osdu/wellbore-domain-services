import pytest

from fastapi import FastAPI, APIRouter
from httpx import AsyncClient
from pydantic import BaseModel
from starlette.requests import Request



from app.helper import utils


@pytest.mark.anyio
async def test_tracing_route_add_path_in_request():

    router = APIRouter()

    class TestResponse(BaseModel):
        url_path: str

    def route_handler(request: Request) -> TestResponse:
        return TestResponse.construct(
            url_path=request.state.traced_route,
        )

    router.get("/testurl", response_model=TestResponse)(route_handler)

    local_app = FastAPI()
    local_app.include_router(router)
    client = AsyncClient(app=local_app, base_url="http://local_app")

    response = (await client.get("http://local_app/testurl")).json()
    assert response['url_path'] == '/testurl'
