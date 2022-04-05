

def test_bob(app_configurable_with_testclient, mock_storage_client_holding_data):
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_client,
        fake_data_partition_id=False,
    )

    record_id = 'bob'
    write_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert write_response.status_code == 200