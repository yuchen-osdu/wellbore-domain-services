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

from app.conf import Config
from app.injector.app_injector import AppInjector, AppInjectorModule
from app.bulk_persistence.dask.blob_storage import (DaskBlobStorageBase,
                                                    DaskBlobStorageLocal)
from app.bulk_persistence.dask.azure import DaskBlobStorageAzure
from app.bulk_persistence.dask.google import DaskBlobStorageGoogle


class DaskStorageInjector(AppInjectorModule):
    """ WORK IN PROGRESS: register factory for dask storage"""
    def configure(self, app_injector: AppInjector):

        blob_storage_localfs: str = Config.get('USE_LOCALFS_BLOB_STORAGE_WITH_PATH')
        if blob_storage_localfs:
            async def _dask_blob_storage_builder():
                return DaskBlobStorageLocal(base_directory=blob_storage_localfs)
            app_injector.register(DaskBlobStorageBase, _dask_blob_storage_builder)

        elif Config.cloud_provider.value == 'az':
            async def build_dask_az_blob_storage() -> DaskBlobStorageBase:
                return DaskBlobStorageAzure()
            app_injector.register(DaskBlobStorageBase, build_dask_az_blob_storage)
        elif Config.cloud_provider.value == 'gcp':
            async def build_dask_gcp_blob_storage() -> DaskBlobStorageBase:
                return DaskBlobStorageGoogle()
            app_injector.register(DaskBlobStorageBase, build_dask_gcp_blob_storage)
        else:
            raise NotImplementedError(f"dask storage not available for provider {Config.cloud_provider.value}")
