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
from unittest.mock import AsyncMock, create_autospec, patch

from fastapi import  HTTPException, status
from odes_storage.exceptions import (
    ResponseHandlingException as OSDUStorageResponseHandlingException,
    ResponseValidationError as OSDUStorageResponseValidationError,
    UnexpectedResponse as OSDUStorageUnexpectedResponse,
)
from osdu_az.exceptions.data_access_error import (
    DataAccessError as OSDUPartitionError,
)
import pytest

from app.clients import StorageRecordServiceClient


storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)


@pytest.fixture
def client(app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_record_service_client_mock
    )
    return client


header = {"Content-Type": "application/json, charset=utf-16"}


def _error_content(code: int, msg: str) -> str:
    return json.dumps({
        "error": {
            "code": code,
            "message": msg
        }
    })


# This test should work also for other exceptions
@pytest.mark.anyio
async def test_storage_client_raise_api_exception(client):
    exception = OSDUStorageUnexpectedResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=_error_content(status.HTTP_401_UNAUTHORIZED, "Not authorized").encode('utf-8'),
        headers=header,
        reason_phrase="An unexpected response")

    with patch.object(storage_record_service_client_mock, 'delete_record', side_effect=exception):
        # when
        response = await client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()
        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == {'error': {'code': 401, 'message': 'Not authorized'}}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_storage_client_raise_response_handling_exception(client):
    exception = OSDUStorageResponseHandlingException(KeyError("Exception"))

    with patch.object(storage_record_service_client_mock, 'delete_record', side_effect=exception):
        response = await client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()

        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == "Exception"
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.anyio
async def test_storage_client_raise_response_validation_error(client):
    exception = OSDUStorageResponseValidationError(
        source=ArithmeticError("Cannot divide by zero"),
        status_code=403,
        content="Cannot divide by zero")

    with patch.object(storage_record_service_client_mock, "delete_record", side_effect=exception):
        response = await client.delete("/ddms/v2/logsets/123456")
        json_res = response.json()

        assert json_res['origin'] == 'osdu-data-ecosystem-storage'
        assert json_res['errors'][0] == "Cannot divide by zero"
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_validation_error_exception(client):
    response = await client.post("/ddms/v2/logsets", data={'test': 'test'})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@patch.object(storage_record_service_client_mock,
              'delete_record',
              AsyncMock(side_effect=KeyError("Error")))
@pytest.mark.anyio
async def test_unhandled_exception(client):
    with pytest.raises(KeyError):
        await client.delete("/ddms/v2/logsets/123456")


@pytest.mark.anyio
async def test_partition_client_raise_api_exception(client):
    exception = OSDUPartitionError(
        status_code=status.HTTP_404_NOT_FOUND,
        message='Failed to retrieve partition. Not found.')

    with patch.object(storage_record_service_client_mock, "get_record", side_effect=exception):
        response = await client.get("/ddms/v2/logs/123456/data")
        json_res = response.json()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert json_res['errors'][0] == 'Failed to retrieve partition. Not found.'


@pytest.mark.parametrize("status_code, msg, called", [(400, "bad request", False),
                                                      (404, "not found", False),
                                                      (500, "internal error", True),
                                                      (502, "bad gateway", True)])
@pytest.mark.anyio
async def test_500_exception_handler(client, nope_logger_fixture, status_code, msg, called):
    with patch("app.routers.about.AboutResponse.construct",
               side_effect=HTTPException(status_code=status_code, detail=msg)):
        response = await client.get('about')
        assert response.status_code == status_code
        assert response.text == '{"detail":"' + msg + '"}'
        assert nope_logger_fixture.exception.called == called
