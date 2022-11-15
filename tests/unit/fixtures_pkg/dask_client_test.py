import pytest

from app.bulk_persistence import DaskException, dask_client
from app.bulk_persistence.dask.localcluster import memory_leeway


@pytest.mark.anyio
async def test_dask_workers_not_enough_ram_available(dask_custom_config, nope_logger_fixture, local_bulk_persistence_config):

    with dask_custom_config(system_memory_mock=42, worker_threads_mock=(10, 10)):

        with pytest.raises(DaskException) as exc:
            # creating the client should throw an exception
            async with dask_client.actx(local_bulk_persistence_config):
                pass
        assert exc.value.args[0].startswith("Not enough memory")


@pytest.mark.parametrize("expected_workers", [
    1, 3, 5
])
@pytest.mark.anyio
async def test_dask_workers_enough_ram_available(dask_custom_config,
                                                 local_bulk_persistence_config,
                                                 expected_workers,
                                                 nope_logger_fixture):

    system_memory = local_bulk_persistence_config.min_worker_memory_recommended * expected_workers + memory_leeway

    with dask_custom_config(system_memory_mock=system_memory, worker_threads_mock=(10, 10)):

        async with dask_client.actx(local_bulk_persistence_config) as client:

            # the workers should use expected memory amount
            expected_worker_memory = (system_memory - memory_leeway) / expected_workers
            assert expected_workers == len(client.cluster.scheduler.workers)

            workers_has_expected_memory = [w.memory_limit == int(expected_worker_memory)
                                           for _, w in client.cluster.scheduler.workers.items()]
            assert all(workers_has_expected_memory)

        assert str(client.cluster.status) == "Status.closed"

