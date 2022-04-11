import time

import pytest

from tests.unit.routers.chunking_test import _create_chunks, _create_record, _create_df_from_response
from app.bulk_persistence.dask.errors import BulkRecordNotFound


def test_invalid_cases(app_configurable_with_testclient,mock_storage_client_holding_data, welllog_v3_record_list):
    storage_client = mock_storage_client_holding_data(welllog_v3_record_list)
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_client,
        fake_data_partition_id=True,
    )

    incorrect_record_id = 'incorrect-id'
    get_stats_response = client.get(f'/ddms/v3/welllogs/{incorrect_record_id}/data/statistics')
    assert get_stats_response.status_code == 404

    get_stats_response = client.post(f'/ddms/v3/welllogs/{incorrect_record_id}/data/statistics')
    assert get_stats_response.status_code == 404

    valid_record_id = welllog_v3_record_list[0].id
    get_stats_response = client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')
    assert get_stats_response.status_code == 404

    version = '123456789'
    invalid_version_id_stats_response = client.get(
        f"/ddms/v3/welllogs/{valid_record_id}/versions/{version}/data/statistics")
    assert invalid_version_id_stats_response.status_code == 404

    with pytest.raises(BulkRecordNotFound):
        client.post(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')


def test_compute_stats(app_configurable_with_testclient, mock_storage_client_holding_data, welllog_v3_record_list):

    _, client = app_configurable_with_testclient(fake_data_partition_id=True)
    record_id = _create_record(client, "WellLog")
    _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20)),
                                                                        (['MD', 'X'], range(10, 30)),
                                                                        (['MD', 'X'], range(25, 40))])

    compute_stats_response = client.post(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert compute_stats_response.status_code == 200

    # todo: it should be replaced by a more robust mechanism that folder existence check in BulkStatistics class
    time.sleep(.5)

    compute_stats_response = client.post(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert compute_stats_response.status_code == 409


def test_get_stats(app_configurable_with_testclient):

    _, client = app_configurable_with_testclient(fake_data_partition_id=True)
    record_id = _create_record(client, "WellLog")
    _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20)),
                                                                        (['MD', 'X'], range(10, 30)),
                                                                        (['MD', 'X'], range(25, 40))])

    compute_stats_response = client.post(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert compute_stats_response.status_code == 200
    # todo: it should be replaced by a more robust mechanism that folder existence check in BulkStatistics class
    time.sleep(1)

    record_response = client.get(f'/ddms/v3/welllogs/{record_id}')
    assert record_response.status_code == 200
    bob = record_response.json()

    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert get_stats_response.status_code == 200

    version = bob['version']
    get_stats_version_response = client.get(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics")
    assert get_stats_version_response.status_code == 200
    df_result_1 = _create_df_from_response(get_stats_version_response)
    assert df_result_1.shape == (2, 9)

    params = {
        'curves': "MD,X"
    }
    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response.status_code == 200
    df_result_2 = _create_df_from_response(get_stats_response)
    assert df_result_2.shape == (2, 9)

    params = {
        'curves': "UnknownColumnName"
    }
    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response.status_code == 404

    params = {
        'curves': "bool-D,string-E"
    }
    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    # todo: Update BulkStatistics class + swagger when only not computable columns are requested, 400 error is expected
    assert get_stats_response.status_code == 400
