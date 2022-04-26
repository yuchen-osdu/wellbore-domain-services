import asyncio
from datetime import datetime
import pandas as pd

from unittest import mock
from app.bulk_persistence.statistics.bulk_statistics import BulkStatistics
import osdu.core.api.storage.exceptions as osdu_storage_exception

from app.bulk_persistence.statistics.models import BulkDataStatisticsMeta, BulkStatisticsStatus
from tests.unit.generate_data import generate_df
from tests.unit.routers.chunking_test import _create_chunks, _create_record, _create_df_from_response, Definitions


def post_welllog_data(client, record_id, columns, range_index):
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions['WellLog']["chunking_url"]

    data_to_send = generate_df(columns, range_index).to_parquet(engine='pyarrow')

    write_response = client.post(f'{chunking_url}/{record_id}/data', data=data_to_send, headers=headers)
    assert write_response.status_code == 200


def create_df_from_dict(response):
    dict_data = response.json()['data']
    return pd.DataFrame.from_dict(dict_data)


def fetch_stats_for_3s(client, record_id):
    api_results = []

    for i in range(6):
        get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
        api_results.append(get_stats_response)
        if get_stats_response.status_code == 200:
            break

        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.5))

    successful_response = [r for r in api_results if r.status_code == 200]
    faulty_responses = [r.content for r in api_results if r.status_code != 200]
    assert successful_response, faulty_responses if faulty_responses else ""
    return successful_response[0]


def test_invalid_cases(app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(fake_data_partition_id=True)
    valid_record_id = _create_record(client, "WellLog")

    # todo: check response error message

    incorrect_record_id = 'incorrect-id'
    get_stats_response = client.get(f'/ddms/v3/welllogs/{incorrect_record_id}/data/statistics')
    assert get_stats_response.status_code == 404
    assert get_stats_response.json().get('origin') == "osdu-data-ecosystem-storage"

    post_stats_response = client.post(f'/ddms/v3/welllogs/{incorrect_record_id}/data/statistics')
    assert post_stats_response.status_code == 404
    assert post_stats_response.json().get('origin') == "osdu-data-ecosystem-storage"

    valid_record_no_bulk_response = client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')
    assert valid_record_no_bulk_response.status_code == 404

    version = '123456789'
    valid_record_invalid_version_response = client.get(
        f"/ddms/v3/welllogs/{valid_record_id}/versions/{version}/data/statistics")
    assert valid_record_invalid_version_response.status_code == 404


def test_with_bulk_no_stats(app_configurable_with_testclient):
    with mock.patch.object(BulkStatistics, '_fetch_statistics_meta_file') as bob:
        bob.side_effect = osdu_storage_exception.ResourceNotFoundException()

        _, client = app_configurable_with_testclient(fake_data_partition_id=True, disable_bulk_consistency=True)
        valid_record_id = _create_record(client, "WellLog")
        post_welllog_data(client, valid_record_id, ['int-A'], range(10))

        valid_record_with_bulk_response = client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')
        assert valid_record_with_bulk_response.status_code == 404
        assert valid_record_with_bulk_response.content == b'{"detail":"Statistics do not exist"}'


def test_with_bulk_stats_not_complete(app_configurable_with_testclient):
    with mock.patch.object(BulkStatistics, '_fetch_statistics_meta_file') as bob:
        _, client = app_configurable_with_testclient(fake_data_partition_id=True, disable_bulk_consistency=True)
        valid_record_id = _create_record(client, "WellLog")

        bob.return_value = BulkDataStatisticsMeta(creation_utc_date=datetime.utcnow(),
                                                  record_id=valid_record_id,
                                                  record_version=str(123456789),
                                                  computation_status=BulkStatisticsStatus.Started)

        post_welllog_data(client, valid_record_id, ['int-A'], range(10))

        valid_record_with_bulk_response = client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')
        assert valid_record_with_bulk_response.status_code == 404
        assert valid_record_with_bulk_response.content == b'{"detail":"Statistics computation not finished yet"}'


def test_double_compute_stats(app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(fake_data_partition_id=True)
    record_id = _create_record(client, "WellLog")
    _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20)),
                                                                        (['MD', 'X'], range(10, 30)),
                                                                        (['MD', 'X'], range(25, 40))])

    fetch_stats_for_3s(client, record_id)

    compute_stats_response = client.post(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert compute_stats_response.status_code == 409


def test_get_stats(app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(fake_data_partition_id=True)
    record_id = _create_record(client, "WellLog")
    _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20)),
                                                                        (['MD', 'X'], range(10, 30)),
                                                                        (['MD', 'X'], range(25, 40))])

    fetch_stats_for_3s(client, record_id)

    record_response = client.get(f'/ddms/v3/welllogs/{record_id}')
    assert record_response.status_code == 200
    record_json = record_response.json()

    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert get_stats_response.status_code == 200

    version = record_json['version']
    get_stats_version_response = client.get(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics")
    assert get_stats_version_response.status_code == 200
    df_result_1 = create_df_from_dict(get_stats_version_response)
    assert df_result_1.shape == (2, 9)

    params = {
        'curves': "MD,X"
    }
    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response.status_code == 200
    df_result_2 = create_df_from_dict(get_stats_response)
    assert df_result_2.shape == (2, 9)

    params = {
        'curves': "UnknownColumnName"
    }
    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response.status_code == 404


def test_get_stats_from_not_computable_columns(app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                 disable_bulk_consistency=True)
    record_id = _create_record(client, "WellLog")
    _create_chunks(client, 'WellLog',
                   record_id=record_id,
                   cols_ranges=[(
                       # ["bool-C", "int-A", "string-B", "string-D"],
                       ['int-A', 'string-B', 'bool-C', 'string-D'],
                       range(20))])

    fetch_stats_for_3s(client, record_id)

    # not computable curves + unknown curves requested => 404
    params = {
        'curves': "bool-D,string-E,UnknownColumn"
    }
    get_stats_response_1 = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response_1.status_code == 404

    # not computable curves requested => 400
    params = {
        'curves': "bool-C,string-D"
    }
    # todo: Update BulkStatistics class + swagger when only not computable columns are requested, 400 error is expected
    get_stats_response_2 = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response_2.status_code == 400


def test_get_stats_after_post_data(app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(fake_data_partition_id=True,
                                                 disable_bulk_consistency=True)
    record_id = _create_record(client, "WellLog")
    post_welllog_data(client, record_id, ['int-A', 'string-B', 'bool-C', 'string-D'], range(10))

    response = fetch_stats_for_3s(client, record_id)
    assert response
    # todo: check stats values
