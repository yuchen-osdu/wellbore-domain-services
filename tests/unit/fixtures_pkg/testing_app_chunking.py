import pytest

from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.bulk_persistence import SessionsStorage

from tests.unit.blob_storage_fsspec import BlobStorageFsspec

async def create_bulk_mocks(local_blob_path: str, local_storage_path: str):

    local_blob_storage = BlobStorageFsspec(base_directory=local_blob_path, protocol="file", auto_mkdir=True)

    local_storage_service = StorageRecordServiceBlobStorage(LocalFSBlobStorage(directory=local_storage_path),
                                                            'myProject', 'myContainer')
    session_storage = SessionsStorage(local_blob_storage)
    return {
        "storage_client_mock": local_storage_service,
        "blob_storage_base_mock": local_blob_storage,
        "sessions_storage_mock": session_storage,
    }


@pytest.fixture
async def testing_app_local_chunking_no_consistency(app_configurable_with_testclient, local_dev_config):
    config = local_dev_config
    local_blob_path = config.get("USE_LOCALFS_BLOB_STORAGE_WITH_PATH")
    local_storage_path = config.get("USE_INTERNAL_STORAGE_SERVICE_WITH_PATH")

    super_mocks = await create_bulk_mocks(local_blob_path=local_blob_path,
                                          local_storage_path=local_storage_path)

    app, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                   disable_bulk_consistency=True,  # Disable consistency
                                                   search_client_mock=None,
                                                   **super_mocks
                                                   )
    yield app, client


@pytest.fixture
async def testing_app_local_chunking_with_consistency(app_configurable_with_testclient, tmp_path_factory):

    super_mocks = await create_bulk_mocks(local_blob_path=str(tmp_path_factory.mktemp(basename="storage-")),
                                          local_storage_path=str(tmp_path_factory.mktemp(basename="blob-")))

    app, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                   disable_bulk_consistency=False,  # Enable consistency
                                                   search_client_mock=None,
                                                   **super_mocks
                                                   )
    yield app, client
