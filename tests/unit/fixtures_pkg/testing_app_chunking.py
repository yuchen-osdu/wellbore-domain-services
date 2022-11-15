import pytest

from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.bulk_persistence import make_local_dask_bulk_storage, dask_client, make_local_dask_storage_parameters, BulkPersistenceConfig
from app.bulk_persistence import SessionsStorage


async def create_bulk_mocks(local_blob_path: str, local_storage_path: str,
                            bulk_config: BulkPersistenceConfig,
                            dask_client: dask_client.DaskDistributedClient):
    from tests.unit.blob_storage_fsspec import BlobStorageFsspec
    dask_storage_mock = await make_local_dask_bulk_storage(base_directory=local_blob_path,
                                                           bulk_config=bulk_config,
                                                           dask_client=dask_client)

    local_dask_parameters = make_local_dask_storage_parameters(local_blob_path)

    # using blob storage over ffspec to make the read/write compatible with what Dask
    local_blob_storage = BlobStorageFsspec(local_blob_path, local_dask_parameters.protocol, **local_dask_parameters.storage_options)

    local_storage_service = StorageRecordServiceBlobStorage(LocalFSBlobStorage(directory=local_storage_path),
                                                            'myProject', 'myContainer')
    session_storage = SessionsStorage(local_blob_storage)
    return {
        "storage_client_mock": local_storage_service,
        "dask_bulk_storage_mock": dask_storage_mock,
        "blob_storage_base_mock": local_blob_storage,
        "sessions_storage_mock": session_storage,
    }


@pytest.fixture
async def testing_app_local_chunking_no_consistency(app_configurable_with_testclient, tmp_path_factory,
                                                    local_bulk_persistence_config):

    super_mocks = await create_bulk_mocks(local_blob_path=str(tmp_path_factory.mktemp(basename="storage-")),
                                          local_storage_path=str(tmp_path_factory.mktemp(basename="blob-")),
                                          bulk_config=local_bulk_persistence_config,
                                          # TODO : instead of calling create,
                                          #   it would be cleaner to explicitly grab the existing client
                                          #   from the app_configurable_with_testclient.app.state
                                          dask_client=await dask_client.create(local_bulk_persistence_config))

    app, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                   disable_bulk_consistency=True,  # Disable consistency
                                                   search_client_mock=None,
                                                   **super_mocks
                                                   )
    yield app, client


@pytest.fixture
async def testing_app_local_chunking_with_consistency(app_configurable_with_testclient, tmp_path_factory,
                                                      local_bulk_persistence_config):

    super_mocks = await create_bulk_mocks(local_blob_path=str(tmp_path_factory.mktemp(basename="storage-")),
                                          local_storage_path=str(tmp_path_factory.mktemp(basename="blob-")),
                                          bulk_config=local_bulk_persistence_config,
                                          # TODO : instead of calling create,
                                          #   it would be cleaner to explicitly grab the existing client
                                          #   from the app_configurable_with_testclient.app.state
                                          dask_client=await dask_client.create(local_bulk_persistence_config))

    app, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                   disable_bulk_consistency=False,  # Enable consistency
                                                   search_client_mock=None,
                                                   **super_mocks
                                                   )
    yield app, client
