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
from unittest.mock import create_autospec, patch

from fastapi import HTTPException
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


@pytest.mark.parametrize("status_code, msg, called", [(400, "bad request", False),
                                                      (404, "not found", False),
                                                      (500, "internal error", True),
                                                      (502, "bad gateway", True)])
@pytest.mark.anyio
async def test_500_exception_handler(client, nope_logger_fixture, status_code, msg, called):
    with patch("app.routers.about.AboutResponse",
               side_effect=HTTPException(status_code=status_code, detail=msg)):
        response = await client.get('about')
        assert response.status_code == status_code
        assert response.text == '{"detail":"' + msg + '"}'
        assert nope_logger_fixture.exception.called == called


@pytest.mark.anyio
async def test_storage_timeout_maps_to_504(nope_logger_fixture):
    from unittest.mock import Mock

    from httpx import TimeoutException
    from odes_storage.exceptions import ResponseHandlingException as OSDUStorageResponseHandlingException
    from starlette.status import HTTP_504_GATEWAY_TIMEOUT

    from app.conf import Config
    from app.errors.client_error import OSDU_DATA_ECOSYSTEM_STORAGE, http_storage_error_handler

    request = Mock()
    request.url = "https://example/api/storage/v2/records"
    timeout = TimeoutException("The read operation timed out")
    with patch.object(Config.de_client_config_timeout, "value", 10):
        response = await http_storage_error_handler(
            request, OSDUStorageResponseHandlingException(timeout)
        )

    assert response.status_code == HTTP_504_GATEWAY_TIMEOUT
    body = json.loads(response.body)
    assert body["origin"] == OSDU_DATA_ECOSYSTEM_STORAGE
    assert len(body["errors"]) == 1
    assert "timeout after 10s" in body["errors"][0]


@pytest.mark.anyio
async def test_storage_response_handling_without_timeout_stays_500(nope_logger_fixture):
    from unittest.mock import Mock

    from odes_storage.exceptions import ResponseHandlingException as OSDUStorageResponseHandlingException
    from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

    from app.errors.client_error import OSDU_DATA_ECOSYSTEM_STORAGE, http_storage_error_handler

    request = Mock()
    request.url = "https://example/api/storage/v2/records"
    response = await http_storage_error_handler(
        request, OSDUStorageResponseHandlingException(ConnectionError("connection reset"))
    )

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    body = json.loads(response.body)
    assert body["origin"] == OSDU_DATA_ECOSYSTEM_STORAGE
    assert body["errors"] == ["connection reset"]

