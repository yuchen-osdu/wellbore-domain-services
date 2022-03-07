import pytest

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.testclient import TestClient

from app.helper.traces import TracingRoute
from app.helper.utils import rename_cloud_role_func, azure_traces_processing
from app.helper import utils

from opencensus.ext.azure.common import utils as azure_utils
from opencensus.ext.azure.common.protocol import (
    Request as AzureRequest,
    Data as AzureEnvelopeData,
    Envelope as AzureEnvelope)


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


def test_rename_cloud_role_func():
    envelope = AzureEnvelope(tags=dict(azure_utils.azure_monitor_context))
    service_name = "test-service-name"

    assert envelope.tags['ai.cloud.role'] != service_name
    rename_cloud_role_func(service_name)(envelope)
    assert envelope.tags['ai.cloud.role'] == service_name


@pytest.mark.parametrize("url_attribute", [
    'a' * 100,
    'b' * (utils._maximum_azure_attribute_length-1),
    'c' * utils._maximum_azure_attribute_length,
    'd' * (utils._maximum_azure_attribute_length+1),
    'e' * (utils._maximum_azure_attribute_length*2),
])
def test_azure_traces_processing(url_attribute):
    envelope = AzureEnvelope()
    envelope.data = AzureEnvelopeData(baseData=AzureRequest(url=url_attribute), baseType='RequestData')

    assert azure_traces_processing(envelope)
    assert len(envelope.data.baseData['url']) <= utils._maximum_azure_attribute_length

    if len(url_attribute) >= utils._maximum_azure_attribute_length:
        assert envelope.data.baseData['url'].endswith('...')
    else:
        assert url_attribute == envelope.data.baseData['url']


