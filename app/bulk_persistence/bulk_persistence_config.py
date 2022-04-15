# Copyright 2022 Schlumberger
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

class BulkPersistenceConfig:
    """
    Single container for the app configuration elements relevant to bulk persistence.
    """

    def __init__(self, min_worker_memory_recommended: int = 512,
                 service_name: str = 'os-wellbore-ddms---local',
                 cloud_provider: str = 'local',
                 default_data_tenant_project_id: str = 'opendes'
        ):
        self._min_worker_memory_recommended = min_worker_memory_recommended
        self._service_name = service_name
        self._cloud_provider = cloud_provider
        self._default_data_tenant_project_id = default_data_tenant_project_id

    @property
    def min_worker_memory_recommended(self) -> int:
        return self._min_worker_memory_recommended

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def cloud_provider(self) -> str:
        return self._cloud_provider

    @property
    def default_data_tenant_project_id(self) -> str:
        return self._default_data_tenant_project_id
