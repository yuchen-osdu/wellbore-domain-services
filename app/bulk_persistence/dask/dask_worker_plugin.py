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
from app.helper.logger import get_logger, init_logger
from app.conf import Config as AppConfig


class DaskWorkerPlugin(WorkerPlugin):

    def __init__(self, service_name, logger=None, register_fsspec_implementation=None) -> None:
        self.worker = None
        self._register_fsspec_implementation = register_fsspec_implementation
        self._service_name = service_name

        super().__init__()
        logger.debug("WorkerPlugin initialised")

    def setup(self, worker):
        init_logger(service_name=self._service_name, config=AppConfig)

        self.worker = worker
        if self._register_fsspec_implementation:
            self._register_fsspec_implementation()

    def teardown(self, worker):
        get_logger().debug(f"Worker '{worker.name}' with id '{worker.id}' is closing - {worker}")

    def transition(self, key, start, finish, *args, **kwargs):
        if finish == 'error':
            exception_text = None
            ts = self.worker.tasks.get(key, None)
            if ts:
                exception_text = ts.exception_text
            get_logger().exception(f"Worker's task '{key}' has failed because of '{exception_text}'")

