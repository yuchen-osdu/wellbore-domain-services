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

from fastapi.testclient import TestClient
from fastapi import Header, status

import pytest
import copy

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage

from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.clients.storage_service_client import StorageRecordServiceClient

from app.helper import traces
from app.auth.auth import require_opendes_authorized_user
from app.middleware import require_data_partition_id
from app.wdms_app import wdms_app, app_injector

from app.utils import Context

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

DATA_PARTITION_ID = 'test_partition'
BASE_HEADERS = {'data-partition-id': DATA_PARTITION_ID}
URL_PREFIX = '/ddms/v2'

acl = {
    "owners": [
        "data.default.owners@opendes.p4d.cloud.slb-ds.com"
    ],
    "viewers": [
        "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
    ]
}

legal = {
    "legaltags": [
        "opendes-public-usa-dataset-1"
    ],
    "otherRelevantDataCountries": ["US", "FR"],
}

trajectory_kind = "opendes:wks:trajectory:1.0.5"
trajectory_id = "opendes:wddms-test_CLA_traj-trajectory:0000"
trajectory_name = "trajectory_test_CLA_traj-trajectory_name"


traj = {
        "acl": acl,
        "legal": legal,
        "kind": trajectory_kind,
        "id": trajectory_id,
        "data": {
            "name": trajectory_name
        }
    }

headers = { "data-partition-id": "DATA_PARTITION_ID" }

prev_data = {"columns": ["col_100X"], "data": [[0], [1], [2]], 'index': [0, 1, 2]}


@pytest.fixture
def client(tmp_path, nope_logger_fixture):
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
def client_with_log(client):
    # Create or update a log record
    response = client.post("/ddms/v2/trajectories", json=[traj], headers=headers)
    assert response.status_code in range(200, 209), "Create or update log failed"

    log_id = response.json()["recordIds"][0]

    # add data to the log
    response = client.post(f"/ddms/v2/trajectories/{trajectory_id}/data", params={"orient": "split"}, json=prev_data, headers=headers)
    assert response.status_code in range(200, 209), "PUT log data failed"

    # get data
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data", headers=headers)
    assert response.status_code in range(200, 209), "GET log data by channels failed"
    assert response.json() == prev_data, "GET log data  response json body should match  data for latest version"

    # get versions
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/versions", headers=headers)
    assert response.status_code == 200, "GET log data failed"

    version_id = response.json()["versions"][1]

    yield client, log_id, version_id

    response = client.delete(f"/ddms/v2/trajectories/{trajectory_id}", headers=headers)
    assert response.status_code in range(200, 209), "Delete test log failed"



@pytest.mark.parametrize("orient_value, data",
[
    (
        "split",
        {
            "columns": ["MD", "X", "Y", "Z"],
            "index": [0, 1, 2],
            "data": [[1.0, 10, 11, 12], [1.5, 20, 21, 22], [2.0, 30, 31, 32]]
        }
    ),
    (
        "columns",
        {
            "MD": {"0": 1.0, "1": 1.5, "2": 2.0},
            "X": {"0": 10, "1": 20, "2": 30},
            "Y": {"0": 11, "1": 21, "2": 31},
            "Z": {"0": 12, "1": 22, "2": 32},
        }
    )
])
def test_traj_bulk(client, orient_value, data):
    traj_cpy = copy.deepcopy(traj)
    traj_cpy['data']['channels'] = [
        {'name': 'X', 'family': 'X_family'},
        {'name': 'NOT_IN_BULK', 'family': 'NOT_IN_BULK_family'},
    ]

    # Create or update a traj record
    response = client.post("/ddms/v2/trajectories", json=[traj_cpy], headers=headers)
    assert response.ok, "Create or update trajectory failed"

    # get data
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data?orient={orient_value}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT, "GET trajectory data should return 204 when trajectory doesn't have data"

    # add data to the traj
    response = client.post(f"/ddms/v2/trajectories/{trajectory_id}/data?orient={orient_value}", json=data, headers=headers)
    assert response.ok, "PUT trajectory data failed"

    # check record
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}", headers=headers)
    assert response.ok, "GET trajectory record failed"
    computed_record = response.json()

    assert computed_record["id"] == trajectory_id, "id in the record should match trajectory id"
    assert computed_record["kind"] == trajectory_kind, "kind in the record should match trajectory kind"
    assert computed_record["data"]["name"] == trajectory_name, "data.name in the record should match trajectory kind"
    assert computed_record["acl"] == acl, "acl in the record should match trajectory acl"
    assert computed_record["legal"] == legal, "legal in the record should match trajectory acl"
    assert computed_record["data"]["bulkURI"],  "trajectory record should have a bulkid"

    computed_channel = {channel["name"]: channel for channel in computed_record["data"]["channels"]}
    for c in ["MD", "X", "Y", 'Z']:
        assert computed_channel[c]['bulkURI'] == computed_record["data"]["bulkURI"] + f":{c}", "bulkid for channel MD should match {data.bulkid}:{c}"
    
    assert computed_channel["X"]["family"] == "X_family", "channels properties should not be overrided"

    assert computed_channel["NOT_IN_BULK"].get('bulkURI', None) is None
    assert computed_channel["NOT_IN_BULK"]["family"] == "NOT_IN_BULK_family", "channels properties should not be deleted if not in bulk"

    # get data
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data?orient={orient_value}", headers=headers)
    assert response.ok, "GET trajectory data failed"
    assert response.json() == data, "GET trajectory data  response json should match trajectory data"

    # get specific channels data
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data", headers=headers, params={'orient': 'columns', 'channels': ['X', 'Y']})
    assert response.ok, "GET trajectory data by channels failed"
    assert response.json() == {
        "X": {
            "0": 10,
            "1": 20,
            "2": 30
        },
        "Y": {
            "0": 11,
            "1": 21,
            "2": 31
        },
    }, "GET trajectory data by channels response json body should match trajectory channels data"

    # get unknow channels
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data?orient=columns&channels=X&channels=Wrong",
                          headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST, "Get unknown channels data should fail with code 400"
    assert response.reason == "Bad Request"
    assert response.text == '{"detail":"\\"[\'Wrong\'] not in index\\""}'


def test_traj_create_and_delete(client):
    response = client.post("/ddms/v2/trajectories", json=[traj], headers=headers)
    assert response.ok
    data = response.json()
    assert data['recordCount'] == 1
    assert data['recordIds'] == [f'{trajectory_id}']
    assert data['skippedRecordIds'] is None

    response = client.delete(f"/ddms/v2/trajectories/{trajectory_id}", headers=headers)
    assert response.ok


@pytest.mark.parametrize("orient_value, data", [("wrong_orient", {}), ("values", {})])
def test_get_data_orient_param_validation_negative(client, orient_value, data):
    # Create or update a traj record
    response = client.post("/ddms/v2/trajectories", json=[traj], headers=headers)
    assert response.ok, "Create or update trajectory failed"

    # get data
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data?orient={orient_value}", headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # add data to the traj
    response = client.post(f"/ddms/v2/trajectories/{trajectory_id}/data?orient={orient_value}", json=data,
                           headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_log_version_data(client_with_log):
    client, log_id, version_id = client_with_log

    # get data for previous version
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/versions/{version_id}/data", headers=headers)
    assert response.status_code == 200, "GET data for previous version failed"
    assert response.json() == prev_data, "response json body should match previous version data"


@pytest.mark.parametrize("orient_value", ["split", "columns"])
def test_log_version_data_orient_param_validation(client_with_log, orient_value):
    client, log_id, version_id = client_with_log

    # get data for previous version
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/versions/{version_id}/data", params={"orient": orient_value}, headers=headers)
    assert response.ok


def test_log_version_data_orient_param_validation_negative(client_with_log):
    client, log_id, version_id = client_with_log

    # get data for previous version
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/versions/{version_id}/data", params={"orient": "wrong"}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
