from unitttest import mock
import pytest

from fastapi import Header, status

from fastapi.testclient import TestClient
from odes_storage.models import Record

from app.middleware import require_data_partition_id
from app.model.model_curated import dipset

from app.context import Context
from app.wdms_app import wdms_app, app_injector
from app.clients import *
from app.auth.auth import require_opendes_authorized_user
from tests.unit.errors.error_handler_test import StorageRecordServiceBlobStorageMock

from tests.unit.test_utils import create_mock_class
from odes_storage.exceptions import UnexpectedResponse
import pandas as pd

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)

tests_parameters = [
    ('/ddms/v2/dipsets', dipset(id="opendes:doc:00000000000000000000000000000000000", data={})),
]

@pytest.fixture
def client():
    async def bypass_authorization():
        # empty method
        pass

    async def set_default_partition(data_partition_id: str =Header('opendes')):
        Context.set_current_with_value(partition_id=data_partition_id)

    async def build_mock_storage():
        return StorageRecordServiceClientMock()

    async def build_mock_search():
        return SearchServiceClientMock()

    app_injector.register(StorageRecordServiceClient, build_mock_storage)
    app_injector.register(SearchServiceClient, build_mock_search)

    # override authentication dependency
    previous_overrides = wdms_app.dependency_overrides

    try:
        wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        client = TestClient(wdms_app)
        yield client
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up

@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_not_found_case_dipset(client, base_url, record_obj):
    record_id = record_obj.id
    exception = UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="not found", content=b'', headers=Header('test'))

    with StorageRecordServiceClientMock.set_throw('get_record', exception):
        # when
        response = client.get(f'{base_url}/{record_id}/dips', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.text.lower()

@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_dip_empty_query_case(client, base_url, record_obj):
    record_id = record_obj.id
    expected_response = Record(id=record_id, kind='xx', acl={'viewers': [], 'owners': []}, legal={}, data={})
    moc_record = mock.AsyncMock(return_value=expected_response)

    with mock.patch.object(StorageRecordServiceClientMock, "get_record", moc_record), \
            mock.patch("app.bulk_persistence.dataframe_persistence.get_dataframe", pd.DataFrame()):
        # when
        response = client.get(f'{base_url}/{record_id}/dips/query',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK
        response = client.get(f'{base_url}/{record_id}/dips/query?minReference=1&maxReference=1',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK
        response = client.get(f'{base_url}/{record_id}/dips/query?classification=test',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK
