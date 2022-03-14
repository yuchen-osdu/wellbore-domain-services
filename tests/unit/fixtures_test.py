import asyncio

from fastapi import Depends
from unittest.mock import AsyncMock

from app.clients.search_service_client import get_search_service
from app.clients.storage_service_client import get_storage_record_service
from app.context import Context, get_ctx


def test_local_dev_config(local_dev_config):

    # local import
    from app.conf import Config

    # assert config is as expected
    assert local_dev_config.dev_mode.value == True
    assert local_dev_config.cloud_provider.value == "local"

    # asserting config has been patched
    assert Config.dev_mode.value == local_dev_config.dev_mode.value
    assert Config.cloud_provider.value == local_dev_config.cloud_provider.value
    assert (
        Config.service_host_search.value == local_dev_config.service_host_search.value
    )
    assert (
        Config.service_host_storage.value == local_dev_config.service_host_storage.value
    )

    assert Config.modules.value == local_dev_config.modules.value


def test_mock_storage_client_holding_well_v2_record_data(
    mock_storage_client_holding_data, well_v2_record_list
):
    """Test the mock_storage_client_holding_data behavior, along with the well_v2_record data itself"""
    storage_client = mock_storage_client_holding_data(well_v2_record_list)

    # grab current eventloop if we already have one, otherwise creates it
    loop = asyncio.get_event_loop()

    w2ids = [w2.id for w2 in well_v2_record_list]
    for w2id in w2ids:
        assert (
            loop.run_until_complete(
                storage_client.get_record(w2id, "fake_data_partition_id")
            )
            == [w for w in well_v2_record_list if w.id == w2id][0]
        )


def test_mock_storage_client_holding_well_v3_record_data(
    mock_storage_client_holding_data, well_v3_record_list
):
    """Test the mock_storage_client_holding_data behavior, along with the well_v2_record data itself"""
    storage_client = mock_storage_client_holding_data(well_v3_record_list)

    # grab current eventloop if we already have one, otherwise creates it
    loop = asyncio.get_event_loop()

    w3ids = [w3.id for w3 in well_v3_record_list]
    for w3id in w3ids:
        assert (
            loop.run_until_complete(
                storage_client.get_record(w3id, "fake_data_partition_id")
            )
            == [w for w in well_v3_record_list if w.id == w3id][0]
        )


def test_mock_storage_client_holding_wellbore_v2_record_data(
    mock_storage_client_holding_data, wellbore_v2_record_list
):
    """Test the mock_storage_client_holding_data behavior, along with the well_v2_record data itself"""
    storage_client = mock_storage_client_holding_data(wellbore_v2_record_list)

    # grab current eventloop if we already have one, otherwise creates it
    loop = asyncio.get_event_loop()

    w2ids = [w2.id for w2 in wellbore_v2_record_list]
    for w2id in w2ids:
        assert (
            loop.run_until_complete(
                storage_client.get_record(w2id, "fake_data_partition_id")
            )
            == [w for w in wellbore_v2_record_list if w.id == w2id][0]
        )


def test_mock_storage_client_holding_wellbore_v3_record_data(
    mock_storage_client_holding_data, wellbore_v3_record_list
):
    """Test the mock_storage_client_holding_data behavior, along with the well_v2_record data itself"""
    storage_client = mock_storage_client_holding_data(wellbore_v3_record_list)

    # grab current eventloop if we already have one, otherwise creates it
    loop = asyncio.get_event_loop()

    w3ids = [w3.id for w3 in wellbore_v3_record_list]
    for w3id in w3ids:
        assert (
            loop.run_until_complete(
                storage_client.get_record(w3id, "fake_data_partition_id")
            )
            == [w for w in wellbore_v3_record_list if w.id == w3id][0]
        )


def test_app_configurable_with_and_without_data_partition(
    app_configurable_with_testclient, mock_storage_client_holding_data, well_v3_record_list
):
    """Test the app configuration"""
    storage_client = mock_storage_client_holding_data(well_v3_record_list)
    app, client = app_configurable_with_testclient(
        storage_client_mock=storage_client,
        fake_data_partition_id=False,
    )

    # no partition needed
    assert client.get("/about").status_code == 200
    # no partition needed but authentication ok
    response = client.get("/version")
    assert response
    # partition needed for any data retrieval
    assert client.post(f"/wells/{well_v3_record_list[0].id}").status_code == 404
    assert client.get(f"/wellbores/123").status_code == 404
    assert client.get(f"/logsets/123").status_code == 404
    assert client.get(f"/trajectories/123").status_code == 404
    assert client.get(f"/logs/123").status_code == 404

    app, client = app_configurable_with_testclient(
        storage_client_mock=storage_client,
        fake_data_partition_id=True
    )

    # no partition needed
    assert client.get("/about").status_code == 200
    # no partition needed but authentication ok
    assert client.get("/version").status_code == 200
    # partition needed for any data retrieval
    assert client.get(f"/wells/{well_v3_record_list[0].id}").status_code == 404
    assert client.get(f"/wellbores/123").status_code == 404
    assert client.get(f"/logsets/123").status_code == 404
    assert client.get(f"/trajectories/123").status_code == 404
    assert client.get(f"/logs/123").status_code == 404


def test_app_configurable_with_unauthorized_client(
    app_configurable_with_testclient,
):
    """Test the app configuration"""

    app, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=False
    )

    # anonymous ok
    assert client.get("/about").status_code == 200
    # not authorized
    assert client.get("/version").status_code == 403

    app, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True
    )

    # anonymous ok
    assert client.get("/about").status_code == 200
    # authorized
    assert client.get("/version").status_code == 200


def test_app_configurable_with_client_and_mocks(
    app_configurable_with_testclient,
):
    """Test the app configuration"""

    # custom mocks for testing the fixture itself
    class StorageClientMock(AsyncMock):
        def mock_name(self):
            return "MyStorageClientMock"

    storage_client_mock = StorageClientMock()

    class SearchClientMock(AsyncMock):
        def mock_name(self):
            return "MySearchClientMock"

    search_client_mock = SearchClientMock()

    app, client = app_configurable_with_testclient(
        search_client_mock=search_client_mock,
        storage_client_mock=storage_client_mock,
    )

    # create a handler that returns the name of the mocks, for validating the app configuration
    async def inside_out_handler(ctx: Context = Depends(get_ctx)):
        return {
            "search": (await get_search_service(ctx)).mock_name(),
            "storage": (await get_storage_record_service(ctx)).mock_name(),
        }

    try:
        # setup the route with the handler
        app.router.add_api_route("/inside_out", inside_out_handler)

        # do the request
        response = client.get("/inside_out").json()

        assert response["search"] == "MySearchClientMock"
        assert response["storage"] == "MyStorageClientMock"

    finally:
        # remove the route we added to not mess with other tests
        app.router.routes = [r for r in app.routes if r.name != inside_out_handler.__name__]

