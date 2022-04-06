

def test_bob(app_configurable_with_testclient,mock_storage_client_holding_data, welllog_v3_record_list
):
    storage_client = mock_storage_client_holding_data(welllog_v3_record_list)
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_client
    )

    record_id = 'wellbore-id-example'
    write_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert write_response.status_code == 200