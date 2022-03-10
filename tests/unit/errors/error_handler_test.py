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

import json
import pytest
import mock
from fastapi import Header, HTTPException

from fastapi.testclient import TestClient
import starlette.status as status

from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.errors.exception_handlers import create_custom_http_exception_handler
from app.middleware import require_data_partition_id
from app.utils import Context
from app.wdms_app import wdms_app
from app.clients import *
from app.helper import traces, logger
from app.auth.auth import require_opendes_authorized_user

from tests.unit.test_utils import create_mock_class
from odes_storage.exceptions import (
    UnexpectedResponse as OSDUStorageUnexpectedResponse,
    ResponseValidationError as OSDUStorageResponseValidationError,
    ResponseHandlingException as OSDUStorageResponseHandlingException
)

from osdu_az.exceptions.data_access_error import DataAccessError as OSDUPartitionError

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)
StorageRecordServiceBlobStorageMock = create_mock_class(StorageRecordServiceBlobStorage)


@pytest.fixture
def client(nope_logger_fixture):
    async def bypass_authorization():
        pass

    async def set_default_partition(data_partition_id: str = Header('opendes')):
        Context.set_current_with_value(partition_id=data_partition_id)

    mock_storage = mock.AsyncMock(return_value=StorageRecordServiceClientMock())
    mock_search = mock.AsyncMock(return_value=SearchServiceClientMock())
    mock_storage_blob = mock.AsyncMock(return_value=StorageRecordServiceBlobStorageMock())

    with mock.patch('app.routers.ddms_v2.logset_ddms_v2.get_storage_record_service', mock_storage):
        with mock.patch('app.routers.ddms_v2.logset_ddms_v2.get_search_service', mock_search):
            with mock.patch('app.routers.ddms_v2.log_ddms_v2.get_storage_record_service', mock_storage_blob):
                with mock.patch('app.routers.record_utils.get_storage_record_service', mock_storage_blob):
                    wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
                    wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
                    client = TestClient(wdms_app)
                    yield client
                    wdms_app.dependency_overrides = {}


header = {"Content-Type": "application/json, charset=utf-16"}


def _error_content(code: int, msg: str) -> str:
    return json.dumps({
        "error": {
            "code": code,
            "message": msg
        }
    })


# This test should work also for other exceptions
def test_storage_client_raise_api_exception(client):
    exception = OSDUStorageUnexpectedResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=_error_content(status.HTTP_401_UNAUTHORIZED, "Not authorized").encode('utf-8'),
        headers=header,
        reason_phrase="An unexpected response")

    with StorageRecordServiceClientMock.set_throw('delete_record', exception):
        # when
        response = client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()
        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == {'error': {'code': 401, 'message': 'Not authorized'}}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_storage_client_raise_response_handling_exception(client):
    exception = OSDUStorageResponseHandlingException(KeyError("Exception"))

    with StorageRecordServiceClientMock.set_throw('delete_record', exception):
        response = client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()

        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == "Exception"
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_storage_client_raise_response_validation_error(client):
    exception = OSDUStorageResponseValidationError(
        source=ArithmeticError("Cannot divide by zero"),
        status_code=403,
        content="Cannot divide by zero")

    with StorageRecordServiceClientMock.set_throw('delete_record', exception):
        response = client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()

        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == "Cannot divide by zero"
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_validation_error_exception(client):
    response = client.post("/ddms/v2/logsets", data={'test': 'test'})
    json_res = response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@mock.patch.object(StorageRecordServiceClientMock,
                   'delete_record',
                   mock.AsyncMock(side_effect=KeyError("Error")))
def test_unhandled_exception(client):
    with pytest.raises(KeyError):
        client.delete("/ddms/v2/logsets/123456")


def test_partition_client_raise_api_exception(client):
    exception = OSDUPartitionError(
        status_code=status.HTTP_404_NOT_FOUND,
        message='Failed to retrieve partition. Not found.')

    with StorageRecordServiceBlobStorageMock.set_throw('get_record', exception):
        response = client.get("/ddms/v2/logs/123456/data")
        json_res = response.json()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert json_res['errors'][0] == 'Failed to retrieve partition. Not found.'


@pytest.fixture()
def create_exception_handler():
    log = mock.MagicMock()
    logger._LOGGER = log
    create_custom_http_exception_handler(wdms_app, logger)
    client = TestClient(wdms_app)
    yield client, log


@pytest.mark.parametrize("status_code, msg, called", [(400, "bad request", False),
                                                    (404, "not found", False),
                                                    (500, "internal error", True),
                                                    (502, "bad gateway", True)])
def test_500_exception_handler(create_exception_handler, status_code, msg, called):
    client, log = create_exception_handler

    with mock.patch("app.routers.about.AboutResponse.construct", side_effect=HTTPException(status_code=status_code, detail=msg)):
        response = client.get('about')
        assert response.status_code == status_code
        assert response.text == '{"detail":"' + msg + '"}'
        assert log.exception.called == called
