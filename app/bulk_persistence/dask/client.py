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
from dask.utils import parse_bytes, format_bytes
from dask.distributed import Client as DaskDistributedClient
from distributed import system, LocalCluster
from distributed.deploy.utils import nprocesses_nthreads

from ..temp_dir import get_temp_dir
from app.conf import Config

HOUR = 3600  # in seconds


class DaskException(Exception):
    pass


class DaskClient:
    # singleton of DaskDistributedClient class
    client: DaskDistributedClient = None

    # Ensure access to critical section is done for only one coroutine
    lock_client: asyncio.Lock = None

    # Minimal amount of memory required for a Dask worker to not get bad performances
    min_worker_memory_recommended = parse_bytes(Config.min_worker_memory.value)

    # Amount of memory Reserved for fastApi server + ProcessPoolExecutors
    memory_leeway = parse_bytes('600Mi')

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
                    get_logger().info(f"Dask using temporary directory: {get_temp_dir()}")

                    n_workers, threads_per_worker, worker_memory_limit = DaskClient._get_dask_configuration(logger)
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
    def _get_system_memory():
        return system.MEMORY_LIMIT

    @staticmethod
    def _available_memory_for_workers():
        """ Return amount of RAM available for Dask's workers after withdrawing RAM required by server itself """
        return max(0, (DaskClient._get_system_memory() - DaskClient.memory_leeway))

    @staticmethod
    def _recommended_workers_and_threads():
        """ Return the recommended numbers of worker and threads according the cpus available provided by Dask """
        return nprocesses_nthreads()

    @staticmethod
    def _get_dask_configuration(logger):
        """
        Return recommended Dask workers configuration
        """
        n_workers, threads_per_worker = DaskClient._recommended_workers_and_threads()
        available_memory_bytes = DaskClient._available_memory_for_workers()
        worker_memory_limit = int(available_memory_bytes / n_workers)

        logger.info(f"Dask client - system.MEMORY_LIMIT: {format_bytes(DaskClient._get_system_memory())} "
                    f"- available_memory_bytes: {format_bytes(available_memory_bytes)} "
                    f"- min_worker_memory_recommended: {format_bytes(DaskClient.min_worker_memory_recommended)} "
                    f"- computed worker_memory_limit: {format_bytes(worker_memory_limit)} for {n_workers} workers")

        if DaskClient.min_worker_memory_recommended > worker_memory_limit:
            n_workers = available_memory_bytes // DaskClient.min_worker_memory_recommended
            if not n_workers >= 1:
                min_memory = DaskClient.min_worker_memory_recommended + DaskClient.memory_leeway
                message = f'Not enough memory available to start Dask worker. ' \
                          f'Please, consider upgrading container memory to {format_bytes(min_memory)}'
                logger.error(f"Dask client - {message} - "
                             f'n_workers: {n_workers} threads_per_worker: {threads_per_worker}, '
                             f'available_memory_bytes: {available_memory_bytes} ')
                raise DaskException(message)

            worker_memory_limit = available_memory_bytes / n_workers
            logger.warning(f"Dask client - available RAM is too low. Reducing number of workers "
                           f"to {n_workers} running with {format_bytes(worker_memory_limit)} of RAM")

        return n_workers, threads_per_worker, worker_memory_limit

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
