import contextlib
from unittest import mock

import pytest

from app.bulk_persistence.dask.localcluster import memory_leeway


@pytest.fixture(scope="module")
def dask_custom_config(local_bulk_persistence_config):

    # a context manager to handle multiple patches to dask.localcluster
    @contextlib.contextmanager
    def configure(*,
                  system_memory_mock=local_bulk_persistence_config.min_worker_memory_recommended + memory_leeway,
                  worker_threads_mock=(2, 1)
                  ):
        with mock.patch("app.bulk_persistence.dask.localcluster.system_memory",
                        mock.Mock(return_value=system_memory_mock)):
            with mock.patch("app.bulk_persistence.dask.localcluster.recommended_workers_and_threads",
                            mock.Mock(return_value=worker_threads_mock)):
                yield system_memory_mock, worker_threads_mock

    return configure
