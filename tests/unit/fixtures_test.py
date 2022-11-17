import pytest
from fastapi import Depends
from unittest.mock import AsyncMock

from app.clients.search_service_client import get_search_service
from app.clients.storage_service_client import get_storage_record_service
from app.context import Context, get_ctx

from app.model.osdu_model import Well, Well110, Well120, Wellbore, Wellbore110, WellboreMarkerSet110, \
    WellboreMarkerSet120, WellboreTrajectory110, WellLog110, WellLog120, Wellbore111, Wellbore120, WellboreMarkerSet121


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


@pytest.mark.anyio
async def test_mock_storage_client_holding_well_v2_record_data(
    mock_storage_client_holding_data, well_v2_record_list
):
    """Test the mock_storage_client_holding_data behavior, along with the well_v2_record data itself"""
    storage_client = mock_storage_client_holding_data(well_v2_record_list)

    w2ids = [w2.id for w2 in well_v2_record_list]
    for w2id in w2ids:
        assert await storage_client.get_record(w2id, "fake_data_partition_id")\
               == [w for w in well_v2_record_list if w.id == w2id][0]


@pytest.mark.anyio
@pytest.mark.parametrize("well_record_data_fixture", ["well_v3_record_list", "well_v3_110_record_list"])
async def test_mock_storage_client_holding_well_v3_record_data(
    mock_storage_client_holding_data, well_record_data_fixture, request
):
    well_record_data = request.getfixturevalue(well_record_data_fixture)
    """Test the mock_storage_client_holding_data behavior, along with the well_v3_record data itself"""
    storage_client = mock_storage_client_holding_data(well_record_data)

    w3ids = [w3.id for w3 in well_record_data]
    for w3id in w3ids:
        assert await storage_client.get_record(w3id, "fake_data_partition_id") \
               == [w for w in well_record_data if w.id == w3id][0]


@pytest.mark.anyio
@pytest.mark.parametrize("well_record_data_fixture", ["well_v3_record_list", "well_v3_110_record_list"])
async def test_mock_storage_client_holding_well_v3_record_with_version_data(
    mock_storage_client_holding_data, well_record_data_fixture, request
):
    well_record_data = request.getfixturevalue(well_record_data_fixture)
    """Test the mock_storage_client_holding_data behavior, along with the well_v3_record data itself"""
    single_record_v0 = well_record_data[0]
    record_id = single_record_v0.id
    single_record_v1 = single_record_v0.copy(deep=True)
    single_record_v0.version = 0
    single_record_v1.version = 1
    single_record_v1.data['FacilityName'] = single_record_v0.data['FacilityName'] + "_updated"

    storage_client = mock_storage_client_holding_data([single_record_v0, single_record_v1])

    # get latest
    assert (await storage_client.get_record(record_id, "fake_data_partition_id")).version == single_record_v1.version

    # get V0
    r = await storage_client.get_record_version(record_id, 0, "fake_data_partition_id")

    assert r.version == 0 and r.data['FacilityName'] == single_record_v0.data['FacilityName']

    # get V1
    r = await storage_client.get_record_version(record_id, 1, "fake_data_partition_id")

    assert r.version == 1 and r.data['FacilityName'] == single_record_v1.data['FacilityName']

    # get versions
    r = await storage_client.get_all_record_versions(record_id, "fake_data_partition_id")
    assert set(r.versions) == {0, 1}


@pytest.mark.anyio
async def test_mock_storage_client_holding_wellbore_v2_record_data(
    mock_storage_client_holding_data, wellbore_v2_record_list
):
    """Test the mock_storage_client_holding_data behavior, along with the well_v2_record data itself"""
    storage_client = mock_storage_client_holding_data(wellbore_v2_record_list)


    w2ids = [w2.id for w2 in wellbore_v2_record_list]
    for w2id in w2ids:
        assert await storage_client.get_record(w2id, "fake_data_partition_id") \
               == [w for w in wellbore_v2_record_list if w.id == w2id][0]



@pytest.mark.anyio
@pytest.mark.parametrize("wellbore_record_data_fixture", ["wellbore_v3_record_list", "wellbore_v3_110_record_list"])
async def test_mock_storage_client_holding_wellbore_v3_record_data(
    mock_storage_client_holding_data, wellbore_record_data_fixture, request
):
    wellbore_record_data = request.getfixturevalue(wellbore_record_data_fixture)
    """Test the mock_storage_client_holding_data behavior, along with the well_v2_record data itself"""
    storage_client = mock_storage_client_holding_data(wellbore_record_data)


    w3ids = [w3.id for w3 in wellbore_record_data]
    for w3id in w3ids:
        assert await storage_client.get_record(w3id, "fake_data_partition_id")\
               == [w for w in wellbore_record_data if w.id == w3id][0]


@pytest.mark.parametrize("well_record_data_fixture", ["well_v3_record_list", "well_v3_110_record_list"])
@pytest.mark.anyio
async def test_app_configurable_with_and_without_data_partition(
    app_configurable_with_testclient, mock_storage_client_holding_data, well_record_data_fixture, request
):
    well_record_data = request.getfixturevalue(well_record_data_fixture)
    """Test the app configuration"""
    storage_client = mock_storage_client_holding_data(well_record_data)
    app, client = app_configurable_with_testclient(
        storage_client_mock=storage_client,
        fake_data_partition_id=False,
    )

    # no partition needed
    assert (await client.get("/about")).status_code == 200
    # no partition needed but authentication ok
    response = client.get("/version")
    assert response
    # partition needed for any data retrieval
    assert (await client.post(f"/wells/{well_record_data[0].id}")).status_code == 404
    assert (await client.get(f"/wellbores/123")).status_code == 404
    assert (await client.get(f"/logsets/123")).status_code == 404
    assert (await client.get(f"/trajectories/123")).status_code == 404
    assert (await client.get(f"/logs/123")).status_code == 404

    app, client = app_configurable_with_testclient(
        storage_client_mock=storage_client,
        fake_data_partition_id=True
    )

    # no partition needed
    assert (await client.get("/about")).status_code == 200
    # no partition needed but authentication ok
    assert (await client.get("/version")).status_code == 200
    # partition needed for any data retrieval
    assert (await client.get(f"/wells/{well_record_data[0].id}")).status_code == 404
    assert (await client.get(f"/wellbores/123")).status_code == 404
    assert (await client.get(f"/logsets/123")).status_code == 404
    assert (await client.get(f"/trajectories/123")).status_code == 404
    assert (await client.get(f"/logs/123")).status_code == 404


@pytest.mark.anyio
async def test_app_configurable_with_unauthorized_client(
    app_configurable_with_testclient,
):
    """Test the app configuration"""

    app, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=False
    )

    # anonymous ok
    assert (await client.get("/about")).status_code == 200
    # not authorized
    assert (await client.get("/version")).status_code == 403

    app, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True
    )

    # anonymous ok
    assert (await client.get("/about")).status_code == 200
    # authorized
    assert (await client.get("/version")).status_code == 200


@pytest.mark.anyio
async def test_app_configurable_with_client_and_mocks(
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
        response = (await client.get("/inside_out")).json()

        assert response["search"] == "MySearchClientMock"
        assert response["storage"] == "MyStorageClientMock"

    finally:
        # remove the route we added to not mess with other tests
        app.router.routes = [r for r in app.routes if r.name != inside_out_handler.__name__]


def test_well100_v3_list(well100_v3_list):
    assert len(well100_v3_list) > 0
    for inst in well100_v3_list:
        Well.validate(inst)


def test_well110_v3_list(well110_v3_list):
    assert len(well110_v3_list) > 0
    for inst in well110_v3_list:
        Well110.validate(inst)


def test_well120_v3_list(well120_v3_list):
    assert len(well120_v3_list) > 0
    for inst in well120_v3_list:
        Well120.validate(inst)


def test_wellbore100_v3_list(wellbore100_v3_list):
    assert len(wellbore100_v3_list) > 0
    for inst in wellbore100_v3_list:
        Wellbore.validate(inst)


def test_wellbore110_v3_list(wellbore110_v3_list):
    assert len(wellbore110_v3_list) > 0
    for inst in wellbore110_v3_list:
        Wellbore110.validate(inst)


def test_wellbore111_v3_list(wellbore111_v3_list):
    assert len(wellbore111_v3_list) > 0
    for inst in wellbore111_v3_list:
        Wellbore111.validate(inst)


def test_wellbore120_v3_list(wellbore120_v3_list):
    assert len(wellbore120_v3_list) > 0
    for inst in wellbore120_v3_list:
        Wellbore120.validate(inst)


def test_welllog110_v3_list(welllog110_v3_list):
    assert len(welllog110_v3_list) > 0
    for inst in welllog110_v3_list:
        WellLog110.validate(inst)


def test_welllog120_v3_list(welllog120_v3_list):
    assert len(welllog120_v3_list) > 0
    for inst in welllog120_v3_list:
        WellLog120.validate(inst)


def test_marker110_v3_list(marker110_v3_list):
    assert len(marker110_v3_list) > 0
    for inst in marker110_v3_list:
        WellboreMarkerSet110.validate(inst)


def test_marker120_v3_list(marker120_v3_list):
    assert len(marker120_v3_list) > 0
    for inst in marker120_v3_list:
        WellboreMarkerSet120.validate(inst)


def test_marker121_v3_list(marker121_v3_list):
    assert len(marker121_v3_list) > 0
    for inst in marker121_v3_list:
        WellboreMarkerSet121.validate(inst)


def test_trajectory110_v3_list(trajectory110_v3_list):
    assert len(trajectory110_v3_list) > 0
    for inst in trajectory110_v3_list:
        WellboreTrajectory110.validate(inst)
