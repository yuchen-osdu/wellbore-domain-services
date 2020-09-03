import pytest
from mockito import when

from fastapi.testclient import TestClient
from fastapi import HTTPException
import starlette.status as status

from odes_storage.models import RecordVersions, CreateUpdateRecordsResponse

from app.wdms_app import wdms_app
from app.model.model_curated import *
from app.clients import *
from app.helper import traces
from app.auth.auth import require_opendes_authorized_user

from tests.unit.test_utils import patch_async, create_mock_class, make_async_do_nothing, make_async_return_value

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.fixture
def client():
    async def bypass_authorization():
        # empty method
        pass

    with patch_async(
            'app.routers.ddms_v2.trajectory_ddms_v2.get_storage_record_service',
            return_value=StorageRecordServiceClientMock()):
        wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
        client = TestClient(wdms_app)
        yield client


@pytest.mark.parametrize("input_id, expected_code, expected_result", [
    ('123456', 200, trajectory(id="123456")),
    ('111111', 404, {'detail': 'Not found'}),
])
def test_get_trajectory(client, input_id, expected_code, expected_result):
    # Use of mockito to change the return of the storage, as it uses async function we need to define dummy async
    # function for returning something awaitable
    async def asyncreturnfn(id, *args, **kwargs):
        if expected_code != 200:
            raise HTTPException(status_code=expected_code, detail=expected_result['detail'])
        return trajectory(id=id)

    with when(StorageRecordServiceClientMock).get_record(...).thenAnswer(asyncreturnfn):
        response = client.get("/ddms/v2/trajectories/123456")
        assert response.status_code == expected_code
        if expected_code == 200:
            assert trajectory(**(response.json())) == expected_result
        else:
            assert expected_result == response.json()


def test_del_trajectory(client):
    with when(StorageRecordServiceClientMock).delete_record(
            id='123456', data_partition_id='opendes').thenAnswer(make_async_do_nothing()):
        response = client.delete("/ddms/v2/trajectories/123456")
        assert response.status_code == status.HTTP_204_NO_CONTENT


def test_get_trajectory_versions(client):
    expected_response = RecordVersions(recordId="123456", versions=["12356", "89693"])

    with when(StorageRecordServiceClientMock).get_all_record_versions(
            id='123456', data_partition_id='opendes').thenAnswer(make_async_return_value(expected_response)):
        response = client.get("/ddms/v2/trajectories/123456/versions")
        assert response.status_code == status.HTTP_200_OK
        assert RecordVersions(**(response.json())) == expected_response


# TODO add a negative test  -- need to forward error codes
def test_get_trajectory_at_version(client):
    expected_response = trajectory(id="123456", version=12356)

    with when(StorageRecordServiceClientMock).get_record_version(
            id='123456',
            version=12356,
            data_partition_id='opendes').thenAnswer(make_async_return_value(expected_response)):
        response = client.get("/ddms/v2/trajectories/123456/versions/12356")
        assert response.status_code == status.HTTP_200_OK
        assert trajectory(**(response.json())) == expected_response


def test_set_trajectory(client):
    expected_response = CreateUpdateRecordsResponse(recordCount=2, recordIds=['rec1', 'rec2'])

    with when(StorageRecordServiceClientMock).create_or_update_records(...).\
            thenAnswer(make_async_return_value(expected_response)):
        response = client.put("/ddms/v2/trajectories", data='[{"id": "rec1"}, {"id": "rec2"}]')
        assert response.status_code == status.HTTP_200_OK
        assert CreateUpdateRecordsResponse(**response.json()) == expected_response
