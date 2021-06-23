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

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_aws.storage.storage_aws import AwsStorage

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from .app_injector import AppInjector, AppInjectorModule
from app.conf import Config


class AwsInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, AwsInjector.build_aws_storage)
        app_injector.register(DaskBulkStorage, AwsInjector.build_aws_dask_blob_storage)

    @staticmethod
    async def build_aws_storage() -> BlobStorageBase:
        return AwsStorage(
            session=None,
            service_account_file=f'{Config.aws_region.value}$${Config.aws_env.value}'
        )

    @staticmethod
    async def build_aws_dask_blob_storage() -> DaskBulkStorage:
        raise NotImplementedError()
