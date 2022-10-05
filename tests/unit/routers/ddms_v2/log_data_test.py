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


import pytest

from fastapi import Header, status
from fastapi.testclient import TestClient

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage

from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.helper import traces
from app.auth.auth import require_opendes_authorized_user
from app.middleware import require_data_partition_id

from app.context import Context
from app.wdms_app import wdms_app, app_injector
from app.clients import StorageRecordServiceClient

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

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
def client(tmp_path):

    async def storage_service_builder(*args, **kwargs):
        return StorageRecordServiceBlobStorage(LocalFSBlobStorage(directory=tmp_path), 'p1', 'c1')

    async def blob_storage_builder(*args, **kwargs):
        return LocalFSBlobStorage(directory=tmp_path)

    async def set_default_partition(data_partition_id: str = Header('opendes')):
        Context.set_current_with_value(partition_id=data_partition_id)

    app_injector.register(BlobStorageBase, blob_storage_builder)
    app_injector.register(StorageRecordServiceClient, storage_service_builder)

    async def do_nothing():
        # empty method
        pass

    wdms_app.dependency_overrides[require_opendes_authorized_user] = do_nothing
    wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition

    yield TestClient(wdms_app)

    wdms_app.dependency_overrides = {}  # clean up


@pytest.fixture
def client_with_log(client, nope_logger_fixture):
    # Create or update a log record
    response = client.post("/ddms/v2/logs", json=[log_payload], headers=headers)
    assert response.status_code in range(200, 209), "Create or update log failed"

    log_id = response.json()["recordIds"][0]

    # add data to the log
    response = client.post(f"/ddms/v2/logs/{log_id}/data", params={"orient": "split"}, json=prev_data, headers=headers)
    assert response.status_code in range(200, 209), "PUT log data failed"

    # get data
    response = client.get(f"/ddms/v2/logs/{log_id}/data", headers=headers)
    assert response.status_code in range(200, 209), "GET log data by channels failed"
    assert response.json() == prev_data, "GET log data  response json body should match  data for latest version"

    # get versions
    response = client.get(f"/ddms/v2/logs/{log_id}/versions", headers=headers)
    assert response.status_code == 200, "GET log data failed"

    version_id = response.json()["versions"][1]

    yield client, log_id, version_id

    response = client.delete(f"/ddms/v2/logs/{log_id}", headers=headers)
    assert response.status_code in range(200, 209), "Delete test log failed"


@pytest.mark.parametrize("orient_value", ["split", "columns"])
def test_log_get_data_orient_param_validation(client_with_log, orient_value):
    client, log_id, _ = client_with_log
    response = client.get(f"/ddms/v2/logs/{log_id}/data", params={"orient":orient_value}, headers=headers)
    assert response.status_code == 200


def test_log_get_orient_param_validation_negative(client_with_log):
    client, log_id, _ = client_with_log
    response = client.get(f"/ddms/v2/logs/{log_id}/data", params={"orient":"wrong_orient"}, headers=headers)
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
def test_log_post_data_orient_param_validation(client_with_log, orient_value, data):
    client, log_id,  _ = client_with_log
    response = client.post(f"/ddms/v2/logs/{log_id}/data", params={"orient": orient_value}, json=data, headers=headers)
    assert response.ok


def test_log_post_data_orient_param_validation_negative(client_with_log):
    client, log_id, _ = client_with_log
    response = client.post(f"/ddms/v2/logs/{log_id}/data", params={"orient": "wrong_orient"}, json={}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_log_version_data(client_with_log):
    client, log_id, version_id = client_with_log

    # get data for previous version
    response = client.get(f"/ddms/v2/logs/{log_id}/versions/{version_id}/data", headers=headers)
    assert response.status_code == 200, "GET data for previous version failed"
    assert response.json() == prev_data, "response json body should match previous version data"


@pytest.mark.parametrize("orient_value", ["split", "columns"])
def test_log_version_data_orient_param_validation(client_with_log, orient_value):
    client, log_id, version_id = client_with_log

    # get data for previous version
    response = client.get(f"/ddms/v2/logs/{log_id}/versions/{version_id}/data", params={"orient": orient_value}, headers=headers)
    assert response.ok


def test_log_version_data_orient_param_validation_negative(client_with_log):
    client, log_id, version_id  = client_with_log

    # get data for previous version
    response = client.get(f"/ddms/v2/logs/{log_id}/versions/{version_id}/data", params={"orient": "wrong"}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY