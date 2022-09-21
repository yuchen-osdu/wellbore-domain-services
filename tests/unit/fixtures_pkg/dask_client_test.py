import pytest

from app.bulk_persistence import DaskException
from app.bulk_persistence.dask.localcluster import memory_leeway
from app.bulk_persistence import DaskClient


@pytest.mark.asyncio
async def test_dask_workers_not_enough_ram_available(dask_client, nope_logger_fixture, local_bulk_persistence_config):

    if DaskClient.client is not None:
        # TODO after moved of a file, it seems to changed the test execution order making the current one irrelevant
        #  since the dask client already exist it won't be created here with the specific parameters set in the test.
        #  therefore the test will fail.
        #  If run lonely it passes.
        pytest.skip("DaskClient.client already created, the test is irrelevant in this case")

    assert DaskClient.client is None
    with dask_client(system_memory_mock=42,
                     worker_threads_mock=(10, 10),
                     autoclose_asynccontext=True
                     ) as dask_client_asynccontext:

        with pytest.raises(DaskException) as exc:
            # creating the client should throw an exception
            async with dask_client_asynccontext() as client_starter:
                await client_starter(local_bulk_persistence_config)

        assert exc.value.args[0].startswith("Not enough memory")


@pytest.mark.parametrize("expected_workers", [
    1, 3, 5
])
@pytest.mark.asyncio
async def test_dask_workers_enough_ram_available(local_bulk_persistence_config,
                                                 expected_workers,
                                                 dask_client,
                                                 nope_logger_fixture):
    if DaskClient.client is not None:
        # TODO after moved of a file, it seems to changed the test execution order making the current one irrelevant
        #  since the dask client already exist it won't be created here with the specific parameters set in the test.
        #  therefore the test will fail.
        #  If run lonely it passes.
        pytest.skip("DaskClient.client already created, the test is irrelevant in this case")

    system_memory = local_bulk_persistence_config.min_worker_memory_recommended * expected_workers + memory_leeway

    with dask_client(system_memory_mock=system_memory,
                     worker_threads_mock=(10, 10),
                     autoclose_asynccontext=True
                     ) as dask_client_asynccontext:

        # the workers should use expected memory amount
        async with dask_client_asynccontext() as client_starter:
            client = await client_starter(local_bulk_persistence_config)
            expected_worker_memory = (system_memory - memory_leeway) / expected_workers
            assert expected_workers == len(client.cluster.scheduler.workers)

            workers_has_expected_memory = [w.memory_limit == int(expected_worker_memory)
                                           for _, w in client.cluster.scheduler.workers.items()]
            assert all(workers_has_expected_memory)
