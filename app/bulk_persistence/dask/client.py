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

import asyncio
import dask

from dask.utils import format_bytes
from dask.distributed import Client as DaskDistributedClient
from distributed import LocalCluster

from app.conf import Config

from .localcluster import get_dask_configuration

HOUR = 3600  # in seconds


class DaskClient:
    # singleton of DaskDistributedClient class
    client: DaskDistributedClient = None

    # Ensure access to critical section is done for only one coroutine
    lock_client: asyncio.Lock = None

    @staticmethod
    async def create() -> DaskDistributedClient:
        if not DaskClient.lock_client:
            DaskClient.lock_client = asyncio.Lock()

        if not DaskClient.client:
            async with DaskClient.lock_client:
                if not DaskClient.client:
                    from app.helper.logger import get_logger
                    logger = get_logger()
                    logger.info(f"Dask client initialization started...")

                    n_workers, threads_per_worker, worker_memory_limit = get_dask_configuration(config=Config, logger=logger)
                    logger.info(f"Dask client worker configuration: {n_workers} workers running with "
                                f"{format_bytes(worker_memory_limit)} of RAM and {threads_per_worker} threads each")

                    # Ensure memory used by workers is freed regularly despite memory leak
                    dask.config.set({'distributed.worker.lifetime.duration': HOUR * 24})
                    dask.config.set({'distributed.worker.lifetime.stagger': HOUR * 1})
                    dask.config.set({'distributed.worker.lifetime.restart': True})
                    logger.info(f"Dask cluster configuration - "
                                f"worker lifetime: {dask.config.get('distributed.worker.lifetime.duration')}s. "
                                f"stagger: {dask.config.get('distributed.worker.lifetime.stagger')}s.")

                    cluster = await LocalCluster(
                        asynchronous=True,
                        processes=True,
                        threads_per_worker=threads_per_worker,
                        n_workers=n_workers,
                        memory_limit=worker_memory_limit,
                        dashboard_address=None
                    )

                    # A worker could be killed when executing a task if lifetime duration elapsed,
                    # "cluster.adapt(min=N, max=N)" ensure the respawn of workers if it happens
                    cluster.adapt(minimum=n_workers, maximum=n_workers)
                    DaskClient.client = await DaskDistributedClient(cluster, asynchronous=True)

                    get_logger().info(f"Dask client initialized : {DaskClient.client}")
        return DaskClient.client

    @staticmethod
    async def close():
        if not DaskClient.lock_client:
            return

        async with DaskClient.lock_client:
            if DaskClient.client:
                # closing the cluster (started independently from the client)
                cluster = await DaskClient.client.cluster
                await cluster.close()
                await DaskClient.client.close()  # or shutdown
                DaskClient.client = None
