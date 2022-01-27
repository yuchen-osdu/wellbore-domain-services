import asyncio


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

