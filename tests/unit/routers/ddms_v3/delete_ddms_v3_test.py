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
import mock

from fastapi.testclient import TestClient

from fastapi import Header, status, HTTPException
from opencensus.trace import base_exporter

from osdu.core.api.storage.blob_storage_base import BlobStorageBase

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.clients import StorageRecordServiceClient
from odes_storage.models import RecordVersions

from app.helper import traces
from app.middleware import require_data_partition_id
from app.auth.auth import require_opendes_authorized_user
from app.routers.delete import delete_bulk_data
from app.utils import Context
from app.wdms_app import wdms_app, app_injector
from tests.unit.test_utils import create_mock_class, nope_logger_fixture

StorageRecordServiceClientMock = mock.AsyncMock()
BlobStorageMock = mock.AsyncMock()

@pytest.fixture
def logger_fixture():
    from app.helper import logger
    logger._LOGGER = mock.MagicMock()
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
        return mock.AsyncMock()

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

record_versions = RecordVersions(record_id='opendes:work-product-component--WellLog:00001234',
                                 versions=[1972724675421999416275969243854301388, 1972724691719041369425630371084748387,
                                           1972724692685381136056789571749686596, 1972724693418066907321024541915238319,
                                           1972724692685381136056789571458786590, 1972724691719041369425637411084748854,
                                           1972724691719041369425637411084487596, 1972724691719041369425637411257894562
                                           ])
record_bulk_uris = ['59c1ab7b-3bc9-4963-976d-815952bc8ddc', None, None, '87be6134-1b8f-43c0-a7f6-384a6a323f60', None,
                    '356eb799-ba19-49ea-814c-cdd8cf87553b', None, 'a764776c-a389-415b-a92c-af8366ce6901']
list_objects = ['bulk/59c1ab7b-3bc9-4963-976d-815952bc8ddc/data/part.0.parquet',
                'bulk/87be6134-1b8f-43c0-a7f6-384a6a323f60/data/part.0.parquet',
                'bulk/356eb799-ba19-49ea-814c-cdd8cf87553b/data/part.0.parquet',
                'bulk/a764776c-a389-415b-a92c-af8366ce6901/data/part.0.parquet']


def test_delete_purge_record(client_delete, logger_fixture):
    record_id = "opendes:work-product-component--WellLog:00001234"
    mock_storage_service_delete_record = mock.AsyncMock(return_value=status.HTTP_204_NO_CONTENT,
                                                        side_effect=status.HTTP_404_NOT_FOUND)
    mock_blob_storage = mock.AsyncMock(return_value=status.HTTP_204_NO_CONTENT,
                                       side_effect=HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                                                 detail="Error 404 not found"))

    mock_storage_list_objects = mock.AsyncMock(return_value=list_objects)
    mock_get_bulk_uri_from_version = mock.AsyncMock(side_effect=record_bulk_uris)
    mock_storage_service_get_all_record_versions = mock.AsyncMock(return_value=record_versions)

    with mock.patch.object(StorageRecordServiceClientMock, "delete_record", mock_storage_service_delete_record), \
         mock.patch.object(StorageRecordServiceClientMock, "get_all_record_versions",
                           mock_storage_service_get_all_record_versions), \
         mock.patch.object(BlobStorageMock, "list_objects", mock_storage_list_objects), \
         mock.patch.object(BlobStorageMock, "delete", mock_blob_storage), \
         mock.patch.object(delete_bulk_data, "_get_bulk_uri_from_version", mock_get_bulk_uri_from_version):

        response = client_delete.delete(
            f"/ddms/v3/record/{record_id}?purge=true",
            headers={"data-partition-id": "testing_partition"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        logger_exception = logger_fixture.exception.mock_calls[0].args[0].split(":")
        assert logger_exception[0] == "List of errors on bulk versions deletion"
        assert logger_exception[1].count("HTTPException(status_code=404, detail='Error 404 not found')") == 4
