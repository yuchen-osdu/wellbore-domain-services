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

from unittest.mock import create_autospec, patch

from fastapi import HTTPException, status
from odes_storage.models import RecordVersions
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
import pytest

from app.bulk_persistence import DaskBulkStorage
from app.clients import StorageRecordServiceClient
from app.routers.delete import delete_bulk_data


storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)
blob_storage_mock = create_autospec(BlobStorageBase, spec_set=True, instance=True)


@pytest.fixture
def client_delete(app_configurable_with_testclient, nope_logger_fixture):
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_record_service_client_mock,
        dask_bulk_storage_mock=create_autospec(DaskBulkStorage, spec_set=True, instance=True),
        blob_storage_base_mock=blob_storage_mock,
    )
    return client


record_bulk_uris = ['59c1ab7b-3bc9-4963-976d-815952bc8ddc', None, None, '87be6134-1b8f-43c0-a7f6-384a6a323f60', None,
                    '356eb799-ba19-49ea-814c-cdd8cf87553b', None, 'a764776c-a389-415b-a92c-af8366ce6901']
list_objects = ['bulk/59c1ab7b-3bc9-4963-976d-815952bc8ddc/data/part.0.parquet',
                'bulk/87be6134-1b8f-43c0-a7f6-384a6a323f60/data/part.0.parquet',
                'bulk/356eb799-ba19-49ea-814c-cdd8cf87553b/data/part.0.parquet',
                'bulk/a764776c-a389-415b-a92c-af8366ce6901/data/part.0.parquet']

versions = [1972724675421999416275969243854301388, 1972724691719041369425630371084748387,
            1972724692685381136056789571749686596, 1972724693418066907321024541915238319,
            1972724692685381136056789571458786590, 1972724691719041369425637411084748854,
            1972724691719041369425637411084487596, 1972724691719041369425637411257894562]

v3_entities = ["welllogs", "wellboretrajectories"]


@pytest.mark.parametrize("url_base_path, record_id", [
    ("/ddms/v3/welllogs", "opendes:work-product-component--WellLog:00001234"),
    ("/ddms/v3/wellboretrajectories", "opendes:work-product-component--WellboreTrajectory:00001234")
])
def test_delete_purge_record(client_delete, nope_logger_fixture, url_base_path, record_id):
    record_versions = RecordVersions(record_id=record_id, versions=versions)

    with patch.object(storage_record_service_client_mock, "delete_record",
                      side_effect=status.HTTP_404_NOT_FOUND), \
         patch.object(storage_record_service_client_mock, "get_all_record_versions",
                      return_value=record_versions), \
         patch.object(blob_storage_mock, "list_objects",
                      return_value=list_objects), \
         patch.object(blob_storage_mock, "delete",
                      side_effect=HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                                detail="Error 404 not found")), \
         patch.object(delete_bulk_data, "_get_bulk_uri_from_version",
                      side_effect=record_bulk_uris):

        response = client_delete.delete(
            f"{url_base_path}/{record_id}?purge=true",
            headers={"data-partition-id": "testing_partition"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        for i in range(4):
            logger_exception = nope_logger_fixture.exception.mock_calls[i].args[0]
            assert logger_exception == "Exception on bulk versions deletion: Error 404 not found"
