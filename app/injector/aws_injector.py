# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
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
from app.conf import Config
from app.context import Context
from app.tenant import resolve_tenant
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_aws.storage.dask_storage_parameters import (
    get_dask_storage_parameters as aws_parameters,
)
from osdu_aws.storage.storage_aws import AwsStorage

from .app_injector import AppInjector, AppInjectorModule


class AwsInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, AwsInjector.build_aws_storage)
        app_injector.register(DaskBulkStorage, partial(AwsInjector.build_aws_dask_blob_storage,
                                                       app_injector=app_injector,
                                                       bulk_config=get_config()))
    @staticmethod
    async def build_aws_storage() -> BlobStorageBase:
        return AwsStorage(
             session=None,
             service_account_file=f'{Config.aws_region.value}$${Config.aws_env.value}'
         )


    @staticmethod
    async def build_aws_dask_blob_storage(app_injector: AppInjector,
                                          bulk_config: BulkPersistenceConfig) -> DaskBulkStorage:
        ctx: Context = Context.current()
        tenant = await resolve_tenant(ctx.partition_id)
        service_account_file = f'{Config.aws_region.value}$${Config.aws_env.value}'
        params = await aws_parameters(tenant, service_account_file)
        dask_client = await app_injector.get(DaskDistributedClient)
        return await DaskBulkStorage.create(params, bulk_config, dask_client)
