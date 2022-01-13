from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.testclient import TestClient

from app.helper.traces import TracingRoute


def test_TracingRoute_add_path_in_Request():

    router = APIRouter(route_class=TracingRoute)

    class TestResponse(BaseModel):
        url_path: str

    def route_handler(request: Request) -> TestResponse:
        return TestResponse.construct(
            url_path=request.state.traced_route,
        )

    router.get("/testurl", response_model=TestResponse)(route_handler)

    client = TestClient(router)

    response = client.get("/testurl").json()
    assert response['url_path'] == '/testurl'
