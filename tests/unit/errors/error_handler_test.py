import json

import httpx
import pytest
from mockito import when

from fastapi.testclient import TestClient
import starlette.status as status

from app.wdms_app import wdms_app
from app.clients import *
from app.helper import traces
from app.auth.auth import require_opendes_authorized_user

from tests.unit.test_utils import patch_async, create_mock_class, make_async_do_nothing, make_async_return_value

from odes_storage.exceptions import (
    UnexpectedResponse as OSDUStorageUnexpectedResponse,
    ResponseValidationError as OSDUStorageResponseValidationError,
    ResponseHandlingException as OSDUStorageResponseHandlingException
)

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)


@pytest.fixture
def client():
    async def bypass_authorization():
        pass

    with patch_async(
            'app.routers.ddms_v2.logset_ddms_v2.get_storage_record_service',
            return_value=StorageRecordServiceClientMock()):
        with patch_async(
                'app.routers.ddms_v2.logset_ddms_v2.get_search_service',
                return_value=SearchServiceClientMock()):
            wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
            client = TestClient(wdms_app)
            yield client
            wdms_app.dependency_overrides = {}


header = httpx.Headers({"Content-Type": "application/json, charset=utf-16"})


def _error_content(code: int, msg: str) -> str:
    return json.dumps({
        "error": {
            "code": code,
            "message": msg
        }
    })


# This test should work also for other exceptions
def test_storage_client_raise_api_exception(client):
    content = _error_content(401, "Not athorized")

    with when(StorageRecordServiceClientMock).delete_record(
            id='123456', data_partition_id='opendes').thenRaise(
        OSDUStorageUnexpectedResponse(status_code=401, content=content,
                                      headers=header,
                                      reason_phrase="An unexpected response")):
        response = client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()
        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == "An unexpected response"
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_storage_client_raise_response_handling_exception(client):
    with when(StorageRecordServiceClientMock).delete_record(
            id='123456', data_partition_id='opendes').thenRaise(
        OSDUStorageResponseHandlingException(KeyError("Exception"))):
        response = client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()
        print(json_res)
        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == "Exception"
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_storage_client_raise_response_validation_error(client):
    with when(StorageRecordServiceClientMock).delete_record(
            id='123456', data_partition_id='opendes').thenRaise(
        OSDUStorageResponseValidationError(source=ArithmeticError("Cannot devide by zero"), status_code=403,
                                           content="Cannot devide by zero")):
        response = client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()
        print(json_res)
        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == "Cannot devide by zero"
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_validation_error_exception(client):
    response = client.put("/ddms/v2/logsets", data={'test': 'test'})
    json_res = response.json()
    assert len(json_res['errors']) == 1
    assert json_res['errors'][0]
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_unhandled_exception(client):
    with when(StorageRecordServiceClientMock).delete_record(
            id='123456', data_partition_id='opendes').thenRaise(
        KeyError("Error")):
        try:
            response = client.delete("/ddms/v2/logsets/123456")
            json_res = response.json()
            assert json_res['errors'][0] == "Internal server error"
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            print("Hello")
        except Exception as e:
            assert isinstance(e, KeyError)
