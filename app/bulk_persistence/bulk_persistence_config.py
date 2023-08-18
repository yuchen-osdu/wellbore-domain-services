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

from typing import Callable
from dask.utils import parse_bytes


MAX_COLUMNS_RETURN = 500
MAX_COLUMNS_WRITE_CHUNK = 500


class BulkPersistenceConfig:
    """
    Single container for the app configuration elements relevant to bulk persistence.
    """

    def __init__(self, min_worker_memory: str = "512Mi",
                 dask_data_ipc: str = 'dask_native',
                 service_name: str = 'os-wellbore-ddms---local',
                 dask_enabled_on_read: bool = True,
                 dask_enabled_on_write: bool = True,
                 bulk_worker_host: str = ""
                 ):
        self._min_worker_memory_recommended = parse_bytes(min_worker_memory)
        self._dask_data_ipc = dask_data_ipc
        self._service_name = service_name
        self.dask_enabled_on_read = dask_enabled_on_read
        self.dask_enabled_on_write = dask_enabled_on_write
        self.bulk_worker_host = bulk_worker_host

    @property
    def is_dask_enabled(self):
        return self.dask_enabled_on_read or self.dask_enabled_on_write

    @property
    def min_worker_memory_recommended(self) -> int:
        return self._min_worker_memory_recommended

    @property
    def dask_data_ipc(self) -> str:
        return self._dask_data_ipc

    @property
    def service_name(self) -> str:
        return self._service_name


def set_config_getter(getter: Callable[[], BulkPersistenceConfig]):
    set_config_getter._getter = getter

set_config_getter._getter = None


def get_config() -> BulkPersistenceConfig:
    assert set_config_getter._getter, "config getter not set"
    return set_config_getter._getter()
