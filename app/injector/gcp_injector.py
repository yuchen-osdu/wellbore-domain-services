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
from osdu_gcp.storage.blob_storage_gcp import GCloudAioStorage

from app.utils import get_http_client_session
from .app_injector import AppInjector, AppInjectorModule
from app.context import Context
from app.bulk_persistence import resolve_tenant
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from osdu_gcp.storage.dask_storage_parameters import get_dask_storage_parameters as gcp_parameters


class GCPInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, GCPInjector.build_gcp_blob_storage)
        app_injector.register(DaskBulkStorage, GCPInjector.build_dask_gcp_blob_storage)

    @staticmethod
    async def build_gcp_blob_storage(*args, **kwargs) -> BlobStorageBase:
        ctx: Context = Context.current()
        # TODO to be reviewed
        tenant = await resolve_tenant(ctx.partition_id)
        return GCloudAioStorage(
            session=get_http_client_session(),
            service_account_file=tenant.credentials
        )

    @staticmethod
    async def build_dask_gcp_blob_storage() -> DaskBulkStorage:
        ctx: Context = Context.current()
        tenant =  await resolve_tenant(ctx.partition_id)
        params = await gcp_parameters(tenant)
        return await DaskBulkStorage.create(params)

