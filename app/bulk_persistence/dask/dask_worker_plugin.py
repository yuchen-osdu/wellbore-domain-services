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

from dask.distributed import WorkerPlugin
from app.helper.logger import get_logger


class DaskWorkerPlugin(WorkerPlugin):

    def __init__(self, logger=None, register_fsspec_implementation=None) -> None:
        self.worker = None
        global _LOGGER
        _LOGGER = logger

        self._register_fsspec_implementation = register_fsspec_implementation
        super().__init__()
        get_logger().debug("WorkerPlugin initialised")

    def setup(self, worker):
        self.worker = worker
        if self._register_fsspec_implementation:
            self._register_fsspec_implementation()

    def transition(self, key, start, finish, *args, **kwargs):
        if finish == 'error':
            # exc = self.worker.exceptions[key]
            get_logger().exception(f"Task '{key}' has failed with exception")