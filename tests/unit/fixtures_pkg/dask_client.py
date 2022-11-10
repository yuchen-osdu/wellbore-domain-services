import contextlib
from unittest import mock

import pytest

from app.bulk_persistence import DaskClient
from app.bulk_persistence.dask.localcluster import memory_leeway


@pytest.fixture(scope="module")
def dask_client(event_loop, local_bulk_persistence_config):

    # a context manager to handle the mocks to configure the singleton
    @contextlib.contextmanager
    def configure(*,
                  system_memory_mock=local_bulk_persistence_config.min_worker_memory_recommended + memory_leeway,
                  worker_threads_mock=(2, 1),
                  autoclose_asynccontext=True
                  ):
        with mock.patch("app.bulk_persistence.dask.localcluster.system_memory",
                        return_value=system_memory_mock),\
                mock.patch("app.bulk_persistence.dask.localcluster.recommended_workers_and_threads",
                           return_value=worker_threads_mock):

            if autoclose_asynccontext:
                # an async context manager to handle the daskclient close() coroutine function
                @contextlib.asynccontextmanager
                async def start():
                    try:
                        # CAREFUL: this is for the test to await for it (required to be usable in app fixture).
                        yield DaskClient.create  #TODO : call with parameters here to specify test env for dask ?
                        # because of the async close, we need a coroutine,
                        # and therefore an async context manager
                        # to ensure dask is properly closed in the test using it
                    finally:
                        # we also need a try finally in case the create() itself is triggering an exception.
                        # As the context manager will not take care of this,
                        # we still should call close() to cleanup what should be cleaned.
                        await DaskClient.close()

                yield start

            else:

                # return a coroutine, it is the responsibility of the test to await on it
                # within its own eventloop
                yield DaskClient.create

                # the caller must also call Daskclient.close()

    return configure
