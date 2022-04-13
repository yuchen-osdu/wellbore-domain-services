from logging import Logger

from dask.utils import format_bytes, parse_bytes

from distributed import system
from distributed.deploy.utils import nprocesses_nthreads

#from app.conf import Config


class DaskException(Exception):
    pass


# Amount of memory Reserved for fastApi server + ProcessPoolExecutors
memory_leeway = parse_bytes("600Mi")


def min_worker_memory_recommended(config):
    """Minimal amount of memory required for a Dask worker to not get bad performances"""
    return parse_bytes(config.min_worker_memory.value)


def system_memory():
    """returns the detected memory limit for this system (done by distributed)"""
    return system.MEMORY_LIMIT


def available_memory_for_workers():
    """Return amount of RAM available for Dask's workers after withdrawing RAM required by server itself"""
    return max(0, (system_memory() - memory_leeway))


def recommended_workers_and_threads():
    """ Return the recommended numbers of worker and threads according the cpus available provided by Dask """
    return nprocesses_nthreads()


def get_dask_configuration(*, config, logger: Logger):
    """
    Return recommended Dask workers configuration
    """
    n_workers, threads_per_worker = recommended_workers_and_threads()
    available_memory_bytes = available_memory_for_workers()
    worker_memory_limit = int(available_memory_bytes / n_workers)

    logger.info(
        f"Dask client - system.MEMORY_LIMIT: {format_bytes(system_memory())} "
        f"- available_memory_bytes: {format_bytes(available_memory_bytes)} "
        f"- min_worker_memory_recommended: {format_bytes(min_worker_memory_recommended(config))} "
        f"- computed worker_memory_limit: {format_bytes(worker_memory_limit)} for {n_workers} workers"
    )

    if min_worker_memory_recommended(config) > worker_memory_limit:
        n_workers = available_memory_bytes // min_worker_memory_recommended(config)
        if not n_workers >= 1:
            min_memory = min_worker_memory_recommended(config) + memory_leeway
            message = (
                f"Not enough memory available to start Dask worker. "
                f"Please, consider upgrading container memory to {format_bytes(min_memory)}"
            )
            logger.error(
                f"Dask client - {message} - "
                f"n_workers: {n_workers} threads_per_worker: {threads_per_worker}, "
                f"available_memory_bytes: {available_memory_bytes} "
            )
            raise DaskException(message)

        worker_memory_limit = available_memory_bytes / n_workers
        logger.warning(
            f"Dask client - available RAM is too low. Reducing number of workers "
            f"to {n_workers} running with {format_bytes(worker_memory_limit)} of RAM"
        )

    return n_workers, threads_per_worker, worker_memory_limit


