import pytest

from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.bulk_persistence import make_local_dask_bulk_storage
from app.bulk_persistence import SessionsStorage


async def create_bulk_mocks(local_blob_path: str, local_storage_path: str):
    local_blob_storage = LocalFSBlobStorage(directory=local_blob_path)
    local_storage_service = StorageRecordServiceBlobStorage(local_blob_storage, 'myProject', 'myContainer')
    session_storage = SessionsStorage(local_blob_storage)
    dask_storage_mock = await make_local_dask_bulk_storage(base_directory=local_storage_path)

    return {
        "storage_client_mock": local_storage_service,
        "dask_bulk_storage_mock": dask_storage_mock,
        "blob_storage_base_mock": local_blob_storage,
        "sessions_storage_mock": session_storage,
    }


@pytest.fixture
async def testing_app_local_chunking_no_consistency(app_configurable_with_testclient, tmp_path_factory):

    super_mocks = await create_bulk_mocks(local_blob_path=str(tmp_path_factory.mktemp(basename="storage-")),
                                          local_storage_path=str(tmp_path_factory.mktemp(basename="blob-")))

    app, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                   disable_bulk_consistency=True,
                                                   search_client_mock=None,
                                                   **super_mocks
                                                   )
    yield app, client


@pytest.fixture
async def testing_app_local_chunking_with_consistency(app_configurable_with_testclient, tmp_path_factory):

    super_mocks = await create_bulk_mocks(local_blob_path=str(tmp_path_factory.mktemp(basename="storage-")),
                                          local_storage_path=str(tmp_path_factory.mktemp(basename="blob-")))

    app, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                   disable_bulk_consistency=False,
                                                   search_client_mock=None,
                                                   **super_mocks
                                                   )
    yield app, client
