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
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_baremetal.storage.storage_baremetal import S3Storage

from .app_injector import AppInjector, AppInjectorModule


class BaremetalInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, BaremetalInjector.build_baremetal_storage)

    @staticmethod
    async def build_baremetal_storage() -> BlobStorageBase:
        return S3Storage()
