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
from app.utils import get_http_client_session
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_gcp.storage.blob_storage_gcp import GCloudAioStorage
from osdu_gcp.storage.dask_storage_parameters import (
    get_dask_storage_parameters as gc_parameters,
)

from .app_injector import AppInjector, AppInjectorModule


class GCInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, GCInjector.build_gc_blob_storage)
        app_injector.register(DaskBulkStorage, partial(GCInjector.build_dask_gc_blob_storage,
                                                       app_injector=app_injector,
                                                       bulk_config=get_config()))

    @staticmethod
    async def build_gc_blob_storage(*args, **kwargs) -> BlobStorageBase:
        ctx: Context = Context.current()
        # TODO to be reviewed
        tenant = await resolve_tenant(ctx.partition_id)
        return GCloudAioStorage(
            session=get_http_client_session(),
            service_account_file=tenant.credentials
        )

    @staticmethod
    async def build_dask_gc_blob_storage(app_injector: AppInjector,
                                          bulk_config: BulkPersistenceConfig) -> DaskBulkStorage:
        ctx: Context = Context.current()
        tenant = await resolve_tenant(ctx.partition_id)
        params = await gc_parameters(tenant)
        dask_client = await app_injector.get(DaskDistributedClient)
        return await DaskBulkStorage.create(params, bulk_config, dask_client)
