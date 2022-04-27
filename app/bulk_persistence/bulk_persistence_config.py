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
                 max_columns_return: int = 500,
                 max_columns_per_chunk_write: int = 500,
                 dask_data_ipc: str = 'dask_native',
                 service_name: str = 'os-wellbore-ddms---local'
        ):
        self._min_worker_memory_recommended = min_worker_memory_recommended
        self._max_columns_return = max_columns_return
        self._max_columns_per_chunk_write = max_columns_per_chunk_write
        self._dask_data_ipc = dask_data_ipc
        self._service_name = service_name

    @property
    def min_worker_memory_recommended(self) -> int:
        return self._min_worker_memory_recommended

    @property
    def max_columns_return(self) -> int:
        return self._max_columns_return

    @property
    def max_columns_per_chunk_write(self) -> int:
        return self._max_columns_per_chunk_write

    @property
    def dask_data_ipc(self) -> str:
        return self._dask_data_ipc

    @property
    def service_name(self) -> str:
        return self._service_name


# Global BulkPersistenceConfig instance, for intra-module usage
Config = BulkPersistenceConfig()

# Exported external BulkPersistenceConfig setup
def setup_bulk_persistence(config: BulkPersistenceConfig):
    global Config
    Config = config


