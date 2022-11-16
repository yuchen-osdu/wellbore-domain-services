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

import anyio

import contextlib
from typing import Optional

import dask
from dask.distributed import Client as DaskDistributedClient
from dask.utils import format_bytes
from distributed import LocalCluster

from ..bulk_persistence_config import BulkPersistenceConfig
from .localcluster import get_dask_configuration

_HOUR = 3600  # in seconds

_client: Optional[DaskDistributedClient] = None
_cluster: Optional[LocalCluster] = None

# Ensure access to critical section is done for only one coroutine
_lock_client: Optional[anyio.Lock] = None


async def create(config: BulkPersistenceConfig) -> DaskDistributedClient:
    global _lock_client, _client, _cluster

    if not _lock_client:
        _lock_client = anyio.Lock()

    async with _lock_client:
        if not _client:
            from app.helper.logger import get_logger
            logger = get_logger()
            logger.info(f"Dask client initialization started...")

            n_workers, threads_per_worker, worker_memory_limit = get_dask_configuration(config=config, logger=logger)
            logger.info(f"Dask client worker configuration: {n_workers} workers running with "
                        f"{format_bytes(worker_memory_limit)} of RAM and {threads_per_worker} threads each")

            # Ensure memory used by workers is freed regularly despite memory leak
            dask.config.set({'distributed.worker.lifetime.duration': _HOUR * 24})
            dask.config.set({'distributed.worker.lifetime.stagger': _HOUR * 1})
            dask.config.set({'distributed.worker.lifetime.restart': True})
            logger.info(f"Dask cluster configuration - "
                        f"worker lifetime: {dask.config.get('distributed.worker.lifetime.duration')}s. "
                        f"stagger: {dask.config.get('distributed.worker.lifetime.stagger')}s.")

            _cluster = await LocalCluster(
                asynchronous=True,
                processes=True,
                threads_per_worker=threads_per_worker,
                n_workers=n_workers,
                memory_limit=worker_memory_limit,
                dashboard_address=None
            )

            # A worker could be killed when executing a task if lifetime duration elapsed,
            # "cluster.adapt(min=N, max=N)" ensure the respawn of workers if it happens
            _cluster.adapt(minimum=n_workers, maximum=n_workers)
            _client = await DaskDistributedClient(_cluster, asynchronous=True)

            get_logger().info(f"Dask client initialized : {_client}")

    return _client


async def close():
    global _cluster, _client

    if not _lock_client:
        return

    async with _lock_client:
        if _cluster:
            # explicitly closing the cluster is necessary
            # since it has been started independently of the client
            await _cluster.close()
            _cluster = None

        if _client:
            await _client.close()  # or shutdown
            _client = None


@contextlib.asynccontextmanager
async def actx(config: BulkPersistenceConfig):
    try:
        client = await create(config)
        yield client

    finally:
        await close()
