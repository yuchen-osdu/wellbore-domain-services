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


from fastapi import status
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
import pytest

from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage


data_partition_id = 'test_partition'

log_payload =   {
    "acl": {
    "owners": [
        "data.default.owners@opendes.p4d.cloud.slb-ds.com"
    ],
    "viewers": [
        "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
    ]
   },
   "data": {
        "name": "13223135351"
   },
   "kind": "opendes:wks:log:0.0.1",
   "legal": {
      "legaltags": [
        "opendes-public-usa-dataset-1"
       ],
       "otherRelevantDataCountries": ["US", "FR"]
    }
   }

headers = {"data-partition-id": data_partition_id}

prev_data = {"columns": ["col_100X"], "data": [[0], [1], [2]], 'index': [0, 1, 2]}


@pytest.fixture
def client(tmp_path, app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(
        storage_client_mock=StorageRecordServiceBlobStorage(LocalFSBlobStorage(directory=tmp_path), 'p1', 'c1'),
        blob_storage_base_mock=LocalFSBlobStorage(directory=tmp_path)
    )

    return client


@pytest.fixture
@pytest.mark.anyio
async def client_with_log(client, nope_logger_fixture):
    # Create or update a log record
    response = await client.post("/ddms/v2/logs", json=[log_payload], headers=headers)
    assert response.status_code in range(200, 209), "Create or update log failed"

    log_id = response.json()["recordIds"][0]

    # add data to the log
    response = await client.post(f"/ddms/v2/logs/{log_id}/data", params={"orient": "split"}, json=prev_data, headers=headers)
    assert response.status_code in range(200, 209), "PUT log data failed"

    # get data
    response = await client.get(f"/ddms/v2/logs/{log_id}/data", headers=headers)
    assert response.status_code in range(200, 209), "GET log data by channels failed"
    assert response.json() == prev_data, "GET log data  response json body should match  data for latest version"

    # get versions
    response = await client.get(f"/ddms/v2/logs/{log_id}/versions", headers=headers)
    assert response.status_code == 200, "GET log data failed"

    version_id = response.json()["versions"][1]

    yield client, log_id, version_id

    response = await client.delete(f"/ddms/v2/logs/{log_id}", headers=headers)
    assert response.status_code in range(200, 209), "Delete test log failed"


@pytest.mark.parametrize("orient_value", ["split", "columns"])
@pytest.mark.anyio
async def test_log_get_data_orient_param_validation(client_with_log, orient_value):
    client, log_id, _ = client_with_log
    response = await client.get(f"/ddms/v2/logs/{log_id}/data", params={"orient":orient_value}, headers=headers)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_log_get_orient_param_validation_negative(client_with_log):
    client, log_id, _ = client_with_log
    response = await client.get(f"/ddms/v2/logs/{log_id}/data", params={"orient":"wrong_orient"}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("orient_value, data",
[
    (
        "split",
        {
            "columns": ["Ref", "col_100X"],
            "index": [0, 1, 2],
            "data": [[0.0, 1001], [0.5, 1002], [1.0, 1003]]
        }
    ),
    (
        "columns",
        {
            "Ref": {"0": 0.0, "1": 0.5, "2": 1.0},
            "col_100X": {"0": 1001, "1": 1002, "2": 1003},
        }
    )
])
@pytest.mark.anyio
async def test_log_post_data_orient_param_validation(client_with_log, orient_value, data):
    client, log_id,  _ = client_with_log
    response = await client.post(f"/ddms/v2/logs/{log_id}/data", params={"orient": orient_value}, json=data, headers=headers)
    assert response.is_success


@pytest.mark.anyio
async def test_log_post_data_orient_param_validation_negative(client_with_log):
    client, log_id, _ = client_with_log
    response = await client.post(f"/ddms/v2/logs/{log_id}/data", params={"orient": "wrong_orient"}, json={}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_log_version_data(client_with_log):
    client, log_id, version_id = client_with_log

    # get data for previous version
    response = await client.get(f"/ddms/v2/logs/{log_id}/versions/{version_id}/data", headers=headers)
    assert response.status_code == 200, "GET data for previous version failed"
    assert response.json() == prev_data, "response json body should match previous version data"


@pytest.mark.parametrize("orient_value", ["split", "columns"])
@pytest.mark.anyio
async def test_log_version_data_orient_param_validation(client_with_log, orient_value):
    client, log_id, version_id = client_with_log

    # get data for previous version
    response = await client.get(f"/ddms/v2/logs/{log_id}/versions/{version_id}/data", params={"orient": orient_value}, headers=headers)
    assert response.is_success


@pytest.mark.anyio
async def test_log_version_data_orient_param_validation_negative(client_with_log):
    client, log_id, version_id  = client_with_log

    # get data for previous version
    response = await client.get(f"/ddms/v2/logs/{log_id}/versions/{version_id}/data", params={"orient": "wrong"}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
