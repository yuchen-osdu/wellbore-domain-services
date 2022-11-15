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

from functools import partial

from app.bulk_persistence import (
    BulkPersistenceConfig,
    DaskBulkStorage,
    DaskDistributedClient,
    get_config,
)
from app.context import Context
from app.tenant import resolve_tenant
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_az.storage.blob_storage_az import AzureAioBlobStorage
from osdu_az.storage.dask_storage_parameters import (
    get_dask_storage_parameters as az_parameters,
)

from .app_injector import AppInjector, AppInjectorModule


class AzureInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, AzureInjector.build_az_blob_storage)
        app_injector.register(DaskBulkStorage, partial(AzureInjector.build_dask_az_blob_storage,
                                                       app_injector=app_injector,
                                                       bulk_config=get_config()))

    @staticmethod
    async def build_az_blob_storage() -> BlobStorageBase:
        return AzureAioBlobStorage()

    @staticmethod
    async def build_dask_az_blob_storage(app_injector: AppInjector, bulk_config: BulkPersistenceConfig) -> DaskBulkStorage:
        ctx: Context = Context.current()
        tenant = await resolve_tenant(ctx.partition_id)
        params = await az_parameters(tenant)
        dask_client = await app_injector.get(DaskDistributedClient)
        return await DaskBulkStorage.create(params, bulk_config, dask_client)
