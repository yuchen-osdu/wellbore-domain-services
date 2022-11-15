from unittest.mock import Mock

import asyncio

import types

import pytest
from unittest import mock

from app.bulk_persistence import dask_client


@pytest.fixture
def local_cluster_mock():

    # we need to mock both the class and the instance given current implementation
    mock_cluster_instance = mock.AsyncMock()
    mock_cluster_instance.close = mock.AsyncMock()
    mock_cluster_instance.adapt = mock.Mock()
    with mock.patch("app.bulk_persistence.dask.client.LocalCluster",
                    new=mock.AsyncMock(return_value=mock_cluster_instance)) as mock_cluster:
        yield mock_cluster, mock_cluster_instance


@pytest.fixture
def dask_distributed_client_mock():

    # we need to mock both the class and the instance given current implementation
    mock_client_instance = mock.AsyncMock()
    mock_client_instance.close = mock.AsyncMock()
    with mock.patch("app.bulk_persistence.dask.client.DaskDistributedClient",
                    new=mock.AsyncMock(return_value=mock_client_instance)) as mock_client:
        mock_client.close = mock.AsyncMock()
        yield mock_client, mock_client_instance


def assert_await_called_once(mock: Mock):
    mock.assert_called_once()
    mock.assert_awaited_once()


@pytest.mark.anyio
async def test_dask_client_create_close_idempotent_sync(nope_logger_fixture, local_cluster_mock, local_bulk_persistence_config, dask_distributed_client_mock):
    """Testing that DaskClient.create() and DaskClient.close() are idempotent when called in sequence"""

    cluster_mock, cluster_instance_mock = local_cluster_mock
    client_mock, client_instance_mock = dask_distributed_client_mock

    # first call
    client = await dask_client.create(local_bulk_persistence_config)
    assert_await_called_once(cluster_mock)
    assert_await_called_once(client_mock)

    # another call
    same_client = await dask_client.create(local_bulk_persistence_config)

    # init has NOT been called again
    assert_await_called_once(cluster_mock)
    assert_await_called_once(client_mock)

    # both client variables are actually the same:
    assert id(client) == id(same_client)

    # close call
    await dask_client.close()
    assert_await_called_once(cluster_instance_mock.close)
    assert_await_called_once(client_instance_mock.close)

    # another close call
    await dask_client.close()

    # close has NOT been called again
    assert_await_called_once(cluster_instance_mock.close)
    assert_await_called_once(client_instance_mock.close)


@pytest.mark.anyio
async def test_dask_client_create_close_idempotent_async(nope_logger_fixture, local_cluster_mock,
                                                   local_bulk_persistence_config, dask_distributed_client_mock):
    """Testing that DaskClient.create() and DaskClient.close() are idempotent when called in parallel"""

    cluster_mock, cluster_instance_mock = local_cluster_mock
    client_mock, client_instance_mock = dask_distributed_client_mock


    # running n start in parallel
    # TODO it would be cleaner to use anyio task_group
    await asyncio.gather(
        *[dask_client.create(local_bulk_persistence_config) for _ in range(8)]
    )

    assert_await_called_once(cluster_mock)
    assert_await_called_once(client_mock)

    # running m stop in parallel
    await asyncio.gather(
        *[dask_client.close()  for _ in range(6)]
    )

    assert_await_called_once(cluster_instance_mock.close)
    assert_await_called_once(client_instance_mock.close)


@pytest.mark.anyio
async def test_dask_client_actx_idempotent(nope_logger_fixture, local_cluster_mock,
                                           dask_distributed_client_mock, local_bulk_persistence_config):

    cluster_mock, cluster_instance_mock = local_cluster_mock
    client_mock, client_instance_mock = dask_distributed_client_mock

    # first call
    async with dask_client.actx(local_bulk_persistence_config):

        assert_await_called_once(cluster_mock)
        assert_await_called_once(client_mock)

        # another call
        async with dask_client.actx(local_bulk_persistence_config):

            # init has NOT been called again
            assert_await_called_once(cluster_mock)
            assert_await_called_once(client_mock)

        assert_await_called_once(cluster_instance_mock.close)
        assert_await_called_once(client_instance_mock.close)

    # close has NOT been called again
    assert_await_called_once(cluster_instance_mock.close)
    assert_await_called_once(client_instance_mock.close)
