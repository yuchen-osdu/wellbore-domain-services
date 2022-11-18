from unittest.mock import create_autospec, patch

from fastapi import Header, status
from odes_storage.exceptions import UnexpectedResponse
from odes_storage.models import Record
import pandas as pd
import pytest


from app.clients import  StorageRecordServiceClient
from app.model.model_curated import dipset


storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)

tests_parameters = [
    ('/ddms/v2/dipsets', dipset(id="opendes:doc:00000000000000000000000000000000000", data={})),
]


@pytest.fixture
def client(app_configurable_with_testclient, nope_logger_fixture):
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_record_service_client_mock,
    )
    return client


@pytest.mark.anyio
@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
async def test_get_record_not_found_case_dipset(client, base_url, record_obj):
    record_id = record_obj.id
    exception = UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="not found", content=b'', headers=Header('test'))

    with patch.object(storage_record_service_client_mock, 'get_record', side_effect=exception):
        # when
        response = await client.get(f'{base_url}/{record_id}/dips', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.text.lower()


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_dip_empty_query_case(client, base_url, record_obj):
    record_id = record_obj.id
    expected_response = Record(id=record_id, kind='xx', acl={'viewers': [], 'owners': []}, legal={}, data={})

    with patch.object(storage_record_service_client_mock, "get_record", return_value=expected_response),\
            patch("app.bulk_persistence.dataframe_persistence.get_dataframe", pd.DataFrame()):
        # when
        response = await client.get(f'{base_url}/{record_id}/dips/query',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK
        response = await client.get(f'{base_url}/{record_id}/dips/query?minReference=1&maxReference=1',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK
        response = await client.get(f'{base_url}/{record_id}/dips/query?classification=test',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK
