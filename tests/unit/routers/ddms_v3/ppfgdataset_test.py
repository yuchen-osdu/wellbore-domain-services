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
import os

from jsonschema.exceptions import ValidationError
from odes_storage.models import CreateUpdateRecordsResponse, Record, RecordVersions
import pytest
from starlette.responses import Response

from app.clients import StorageRecordServiceClient

PPFGDATASET_SAMPLE_FILE = "PPFGDataset120_unit.json"
PPFGDATASET_ID = "namespace:work-product-component--PPFGDataset:bb2f4d26-6446-508a-b137-7239ee1bbea1"
PPFGDATASET_VERSION = 1562066009929332


@pytest.mark.anyio
async def test_get_ppfgdataset_osdu_success(mocker, app_configurable_with_testclient):
    """Happy path test case for GET /ddms/v3/ppfgdataset/{ppfgdatasetid}"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, PPFGDATASET_SAMPLE_FILE), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    expected_response = Record.parse_obj(record_json)

    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )

    response = await client.get(url=f"/ddms/v3/ppfgdataset/{PPFGDATASET_ID}",
                                headers={"content-type": "application/json"})

    assert response.status_code == 200
    assert mocked_storage_client.get_record.called_once_with(id=PPFGDATASET_ID)


@pytest.mark.anyio
async def test_del_osdu_ppfgdatasetid_success(mocker, app_configurable_with_testclient):
    """Happy path test case for DELETE /ddms/v3/ppfgdataset/{ppfgdatasetid}"""
    expected_response = Response()

    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.delete_record.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )

    response = await client.delete(url=f"/ddms/v3/ppfgdataset/{PPFGDATASET_ID}"
                                   , headers={"content-type": "application/json"})

    assert response.status_code == 204
    assert mocked_storage_client.delete_record.called_once_with(id=PPFGDATASET_ID)


@pytest.mark.anyio
async def test_get_osdu_ppfgdatasetid_versions_success(mocker, app_configurable_with_testclient):
    """Happy path test case for GET /ddms/v3/ppfgdataset/{ppfgdatasetid}/versions"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, PPFGDATASET_SAMPLE_FILE), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    record_versions_data = {
        "recordId": PPFGDATASET_ID,
        "versions": [PPFGDATASET_VERSION]
    }
    expected_response = RecordVersions.parse_obj(record_versions_data)
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record.return_value = Record.parse_obj(record_json)
    mocked_storage_client.get_all_record_versions.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )

    response = await client.get(url=f"/ddms/v3/ppfgdataset/{PPFGDATASET_ID}/versions", headers={"content-type": "application/json"})

    assert response.status_code == 200
    assert response.json() == record_versions_data
    assert mocked_storage_client.get_all_record_versions.called_once_with(id=PPFGDATASET_ID)


async def test_get_osdu_ppfgdatasetid_version_success(mocker, app_configurable_with_testclient):
    """Happy path test case for GET /ddms/v3/ppfgdataset/{ppfgdatasetid}/versions/{version}"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, PPFGDATASET_SAMPLE_FILE), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    expected_response = Record.parse_obj(record_json)
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record_version.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )

    response = await client.get(url=f"/ddms/v3/ppfgdataset/{PPFGDATASET_ID}/versions/{PPFGDATASET_VERSION}", headers={"content-type": "application/json"})

    assert response.status_code == 200
    assert mocked_storage_client.get_record_version.called_once_with(id=PPFGDATASET_ID, version=PPFGDATASET_VERSION)


@pytest.mark.anyio
async def test_post_ppfgdataset_osdu_success(mocker, app_configurable_with_testclient):
    """Happy path test case for POST /ddms/v3/ppfgdataset"""
    expected_response = CreateUpdateRecordsResponse(
        recordCount=1,
        recordIds=[PPFGDATASET_ID],
    )

    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.create_or_update_records.return_value = expected_response

    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, PPFGDATASET_SAMPLE_FILE), "r", encoding="utf-8") as f:
        record_data = f.read()

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )

    response = await client.post(url="/ddms/v3/ppfgdataset", data=record_data, headers={"content-type": "application/json"})

    assert response.status_code == 200
    assert mocked_storage_client.create_or_update_records.call_count == 1



@pytest.mark.anyio
async def test_post_ppfgdataset_osdu_bad_request_on_validation_error(mocker, app_configurable_with_testclient):
    """Validation error test case for POST /ddms/v3/ppfgdataset"""
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_schema_library = mocker.patch("app.routers.ddms_v3.ppfgdataset_ddms_v3.schema_library")
    mocked_schema_library.validate_records.side_effect = ValidationError("Validation Error")

    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, PPFGDATASET_SAMPLE_FILE), "r", encoding="utf-8") as f:
        record_data = f.read()

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )

    response = await client.post(url="/ddms/v3/ppfgdataset", data=record_data, headers={"content-type": "application/json"})

    assert response.status_code == 422
    assert mocked_storage_client.create_or_update_records.call_count == 0




