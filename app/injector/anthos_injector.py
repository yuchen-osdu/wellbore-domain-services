#  Copyright 2022 Google LLC
#  Copyright 2022 EPAM Systems
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from app.bulk_persistence import DaskBulkStorage, get_config
from app.conf import Config
from app.context import Context
from app.tenant import resolve_tenant
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_anthos.storage.dask_storage_parameters import \
    get_dask_storage_parameters as anthos_parameters
from osdu_anthos.storage.storage_anthos import AnthosStorage

from .app_injector import AppInjector, AppInjectorModule


class AnthosInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, AnthosInjector.build_anthos_storage)
        app_injector.register(DaskBulkStorage, AnthosInjector.build_anthos_dask_blob_storage)

    @staticmethod
    async def build_anthos_storage() -> BlobStorageBase:
        return AnthosStorage()

    @staticmethod
    async def build_anthos_dask_blob_storage() -> DaskBulkStorage:
        ctx: Context = Context.current()
        tenant = await resolve_tenant(ctx.partition_id)
        params = await anthos_parameters(tenant)
        return await DaskBulkStorage.create(params, get_config())
