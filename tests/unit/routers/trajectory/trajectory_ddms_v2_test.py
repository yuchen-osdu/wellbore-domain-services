import json
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from fastapi import Header
import pytest

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage

from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.clients.storage_service_client import StorageRecordServiceClient

from app.helper import traces
from app.auth.auth import require_opendes_authorized_user
from app.middleware import require_data_partition_id
from app.wdms_app import wdms_app, app_injector

from app.utils import Context
from tests.unit.test_utils import nope_logger_fixture

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
    "status": None
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

body = {
    "MD": {
        "0": 1.0,
        "1": 1.5,
        "2": 2.0
    },
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
    "Z": {
        "0": 12,
        "1": 22,
        "2": 32
    }
}


@pytest.fixture
def client(nope_logger_fixture):
    with TemporaryDirectory() as tmpdir:
        async def storage_service_builder(*args, **kwargs):
            return StorageRecordServiceBlobStorage(LocalFSBlobStorage(directory=tmpdir), 'p1', 'c1')

        async def blob_storage_builder(*args, **kwargs):
            return LocalFSBlobStorage(directory=tmpdir)

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


def test_traj_bulk(client):
    # Create or update a traj record
    response = client.post("/ddms/v2/trajectories", json=[traj], headers=headers)
    assert response.ok, "Create or update trajectory failed"

    # get data
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data?orient=columns", headers=headers)
    assert response.status_code == 404, "GET trajectory data should return 404 when trajectory doesn't have data"

    # add data to the traj
    response = client.post(f"/ddms/v2/trajectories/{trajectory_id}/data?orient=columns", json=body, headers=headers)
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

    computed_channel = {channel["name"]: channel["bulkURI"] for channel in computed_record["data"]["channels"]}

    assert computed_channel["MD"] == computed_record["data"]["bulkURI"] + ":MD", "bulkid for channel MD should match {data.bulkid}:MD"
    assert computed_channel["X"] == computed_record["data"]["bulkURI"] + ":X",  "bulkid for channel X should match {data.bulkid}:MD"
    assert computed_channel["Y"] == computed_record["data"]["bulkURI"] + ":Y",  "bulkid for channel Y should match {data.bulkid}:MD"
    assert computed_channel["Z"] == computed_record["data"]["bulkURI"] + ":Z",  "bulkid for channel Z should match {data.bulkid}:MD"

    # get data
    response = client.get(f"/ddms/v2/trajectories/{trajectory_id}/data?orient=columns", headers=headers)
    assert response.ok, "GET trajectory data failed"
    assert response.json() == body, "GET trajectory data  response json body should match trajectory data"

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
    assert response.status_code == 400, "Get unknown channels data should fail with code 400"
    assert response.reason == "Bad Request"
    assert response.text == '{"detail":"\\"[\'Wrong\'] not in index\\""}'


def test_traj_create_and_delete(client):
    response = client.post("/ddms/v2/trajectories", json=[traj], headers=headers)
    assert response.ok
    data = response.json()
    assert data == {'recordCount': 1, 'recordIds': [f'{trajectory_id}'], 'skippedRecordIds': None}

    response = client.delete(f"/ddms/v2/trajectories/{trajectory_id}", headers=headers)
    assert response.ok