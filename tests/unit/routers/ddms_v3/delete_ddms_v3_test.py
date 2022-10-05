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
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from fastapi import Header, status, HTTPException

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from odes_storage.models import RecordVersions


from app.bulk_persistence import DaskBulkStorage
from app.clients import StorageRecordServiceClient

from app.helper import traces
from app.middleware import require_data_partition_id
from app.auth.auth import require_opendes_authorized_user
from app.routers.delete import delete_bulk_data
from app.context import Context
from app.wdms_app import wdms_app, app_injector

StorageRecordServiceClientMock = AsyncMock()
BlobStorageMock = AsyncMock()


@pytest.fixture
def logger_fixture():
    from app.helper import logger
    logger._LOGGER = MagicMock()
    yield logger._LOGGER


@pytest.fixture
def client_delete(logger_fixture):
    async def bypass_authorization():
        # empty method
        pass

    async def set_default_partition(data_partition_id: str = Header("opendes")):
        Context.set_current_with_value(partition_id=data_partition_id)

    async def build_mock_storage():
        return StorageRecordServiceClientMock

    async def build_mock_blob_storage():
        return BlobStorageMock

    async def build_mock_dask_bulk_storage():
        return AsyncMock()

    app_injector.register(StorageRecordServiceClient, build_mock_storage)
    app_injector.register(BlobStorageBase, build_mock_blob_storage)
    app_injector.register(DaskBulkStorage, build_mock_dask_bulk_storage)
    # override authentication dependency
    previous_overrides = wdms_app.dependency_overrides

    try:
        wdms_app.dependency_overrides[
            require_opendes_authorized_user
        ] = bypass_authorization
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        client = TestClient(wdms_app)
        yield client
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name="tested-ddms")

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
def test_delete_purge_record(client_delete, logger_fixture, url_base_path, record_id):
    record_versions = RecordVersions(record_id=record_id, versions=versions)

    with patch.object(StorageRecordServiceClientMock, "delete_record",
                      side_effect=status.HTTP_404_NOT_FOUND), \
         patch.object(StorageRecordServiceClientMock, "get_all_record_versions",
                      return_value=record_versions), \
         patch.object(BlobStorageMock, "list_objects",
                      return_value=list_objects), \
         patch.object(BlobStorageMock, "delete",
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
            logger_exception = logger_fixture.exception.mock_calls[i].args[0]
            assert logger_exception == "Exception on bulk versions deletion: Error 404 not found"
