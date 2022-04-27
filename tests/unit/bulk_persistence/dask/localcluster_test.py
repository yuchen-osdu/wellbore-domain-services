from unittest import mock
import pytest
from distributed.deploy.utils import nprocesses_nthreads


from app.bulk_persistence.dask.localcluster import (
    memory_leeway,
    get_dask_configuration,
    DaskException,
)


def test_get_dask_configuration_not_enough_memory(
    local_bulk_persistence_config, nope_logger_fixture
):
    def mock_system_memory():
        return 42

    with mock.patch(
        "app.bulk_persistence.dask.localcluster.system_memory", mock_system_memory
    ):
        with pytest.raises(DaskException) as exc:
            get_dask_configuration(config=local_bulk_persistence_config, logger=nope_logger_fixture)

        assert exc.value.args[0].startswith("Not enough memory")


@pytest.mark.parametrize("memory_space_for_worker", [1, 2, 3, 4, 5, 6, 7, 8])
def test_get_dask_configuration_just_enough_memory(
    memory_space_for_worker, local_bulk_persistence_config, nope_logger_fixture
):
    def mock_system_memory():
        return (
            local_bulk_persistence_config.min_worker_memory_recommended * memory_space_for_worker
            + memory_leeway
        )

    with mock.patch(
        "app.bulk_persistence.dask.localcluster.system_memory", mock_system_memory
    ):
        n_workers, threads_per_worker, worker_memory_limit = get_dask_configuration(
            config=local_bulk_persistence_config, logger=nope_logger_fixture
        )

        # we should have as many worker as memory space allow,
        # but no more than available processes
        assert n_workers == min(memory_space_for_worker, nprocesses_nthreads()[0])

        # the memory limit per worker should be the total (minus leeway) divided by number of workers
        assert worker_memory_limit == (mock_system_memory() - memory_leeway) / n_workers
