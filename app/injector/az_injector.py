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

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_az.storage.blob_storage_az import AzureAioBlobStorage
from .app_injector import AppInjector, AppInjectorModule

from app.bulk_persistence.dask.blob_storage import DaskBlobStorageBase

# Below import should be pull out to dedicated Azure package osdu.core.api.storage
from app.bulk_persistence.dask.azure import DaskBlobStorageAzure


class AzureInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, AzureInjector.build_az_blob_storage)
        app_injector.register(DaskBlobStorageBase, AzureInjector.build_dask_az_blob_storage)

    @staticmethod
    async def build_az_blob_storage() -> BlobStorageBase:
        return AzureAioBlobStorage()

    @staticmethod
    async def build_dask_az_blob_storage() -> DaskBlobStorageBase:
        return DaskBlobStorageAzure()
