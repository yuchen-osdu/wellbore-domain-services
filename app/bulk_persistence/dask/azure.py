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

from logging import getLogger

import adlfs
import fsspec
from app.bulk_persistence.dask.blob_storage import (DaskBlobStorageBase,
                                                    DaskDriverBlobStorage,
                                                    DefaultWorkerPlugin)
from app.helper.logger import get_logger
from osdu_az.storage.blob_storage_az import AzureAioBlobStorage


class AzureBlobFileSystemWithDefaultCredentials(adlfs.AzureBlobFileSystem):
    """ Wrap the azure file system to add credentials if not present
    The Azure credential object cannot be serialized (pickle) to the workers
    so, it needs to be instantiated from the worker.
    """

    def __init__(self, *args, **kwargs):
        has_credential = (
            "credential" in kwargs or "account_key" in kwargs or "connection_string" in kwargs
        )
        if not has_credential:
            kwargs["credential"] = AzureAioBlobStorage()._get_credentials()
        super().__init__(*args, **kwargs)


def register_azure_fsspec():
    fsspec.register_implementation("abfs", AzureBlobFileSystemWithDefaultCredentials)
    fsspec.register_implementation("az", AzureBlobFileSystemWithDefaultCredentials)

class AzureWorkerPlugin(DefaultWorkerPlugin):
    """ worker plugin enables custom code to run at different stages of the Workers' lifecycle
    At startup, we wrap the azure blob storage to add the authentication.
    """
    def setup(self, worker):
        register_azure_fsspec()
        return super().setup(worker)

register_azure_fsspec()

class DaskBlobStorageAzure(DaskBlobStorageBase):
    """Instantiate a DaskDriverBlobStorage with the Azure blob storage file system."""

    async def build_dask_blob_storage(self, tenant):
        az = AzureAioBlobStorage()
        storage_account_name = await az._get_storage_account_name(tenant.data_partition_id)
        storage_options = {'account_name': storage_account_name}

        _dask = DaskDriverBlobStorage(protocol='az',
                                      base_directory=tenant.bucket_name,
                                      storage_options=storage_options)

        if await _dask.init_client():
            await DaskDriverBlobStorage.client.register_worker_plugin(AzureWorkerPlugin,
                                                                      name="AzureWorkerPlugin",
                                                                      logger=getLogger())

        get_logger().debug(f"DASK_CLIENT: {_dask.client}")  # TODO remove dbg
        return _dask
