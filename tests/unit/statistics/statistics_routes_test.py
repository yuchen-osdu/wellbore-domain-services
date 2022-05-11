import asyncio
from datetime import datetime
import pandas as pd

from unittest import mock

import pytest

from app.bulk_persistence.statistics.bulk_statistics import BulkStatistics
import osdu.core.api.storage.exceptions as osdu_storage_exception

from app.bulk_persistence.statistics.models import StatisticsComputationMeta, BulkStatisticsStatus
from tests.unit.generate_data import generate_df
from tests.unit.routers.chunking_test import _create_chunks, _create_record, _create_df_from_response, Definitions


def post_welllog_data(client, record_id, columns, range_index):
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions['WellLog']["chunking_url"]

    data_to_send = generate_df(columns, range_index).to_parquet(engine='pyarrow')

    write_response = client.post(f'{chunking_url}/{record_id}/data', data=data_to_send, headers=headers)
    assert write_response.status_code == 200
    return write_response


def create_df_from_dict(response):
    dict_data = response.json()['data']
    return pd.DataFrame.from_dict(dict_data, orient='index')


def fetch_stats_for_3s(client, record_id, columns=None):
    api_results = []

    params = None
    if columns:
        params = {
            "curves": ",".join(columns)
        }

    for i in range(6):
        get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
        api_results.append(get_stats_response)
        if get_stats_response.status_code == 200:
            break

        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.5))

    successful_response = [r for r in api_results if r.status_code == 200]
    faulty_responses = [r.content for r in api_results if r.status_code != 200]
    assert successful_response, faulty_responses if faulty_responses else ""
    return successful_response[0]


def test_invalid_cases(testing_app_local_chunking_no_consistency):
    _, client = testing_app_local_chunking_no_consistency
    valid_record_id = _create_record(client, "WellLog")

    version = '123456789'
    unknown_record_id = 'test:work-product-component--WellLog:8fef694e8a5a49ec96db9e51c7522bc9'

    get_stats_response = client.get(f'/ddms/v3/welllogs/{unknown_record_id}/data/statistics')
    assert get_stats_response.status_code == 404
    assert get_stats_response.json().get('origin') == "osdu-data-ecosystem-storage"

    post_stats_response = client.post(f"/ddms/v3/welllogs/{unknown_record_id}/versions/{version}/data/statistics")
    assert post_stats_response.status_code == 404
    assert post_stats_response.json().get('origin') == "osdu-data-ecosystem-storage"

    valid_record_no_bulk_response = client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')
    assert valid_record_no_bulk_response.status_code == 404
    assert valid_record_no_bulk_response.json().get("detail") == f"bulk for record {valid_record_id} not found"

    valid_record_invalid_version_response = client.get(
        f"/ddms/v3/welllogs/{valid_record_id}/versions/{version}/data/statistics")
    assert valid_record_invalid_version_response.status_code == 404
    assert valid_record_invalid_version_response.json().get('origin') == "osdu-data-ecosystem-storage"


def test_with_bulk_no_stats(testing_app_local_chunking_no_consistency):
    with mock.patch.object(BulkStatistics, '_fetch_statistics_meta_file') as bob:
        bob.side_effect = osdu_storage_exception.ResourceNotFoundException()

        _, client = testing_app_local_chunking_no_consistency

        valid_record_id = _create_record(client, "WellLog")
        post_welllog_data(client, valid_record_id, ['int-A'], range(10))

        valid_record_with_bulk_response = client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')
        assert valid_record_with_bulk_response.status_code == 404
        assert valid_record_with_bulk_response.content == b'{"errorType":"DATA_NOT_FOUND","message":"Statistics do not exist"}'


def test_with_bulk_stats_not_complete(testing_app_local_chunking_no_consistency):

    with mock.patch.object(BulkStatistics, '_fetch_statistics_meta_file') as bob:
        _, client = testing_app_local_chunking_no_consistency
        valid_record_id = _create_record(client, "WellLog")

        bob.return_value = StatisticsComputationMeta(computationStartDate=datetime.utcnow(),
                                                     recordId=valid_record_id,
                                                     recordVersion=str(123456789),
                                                     computationStatus=BulkStatisticsStatus.Started)

        post_welllog_data(client, valid_record_id, ['int-A'], range(10))

        valid_record_with_bulk_response = client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics')
        assert valid_record_with_bulk_response.status_code == 404
        assert valid_record_with_bulk_response.content \
               == b'{"errorType":"COMPUTATION_NOT_COMPLETE","message":"Statistics computation not finished yet"}'


def test_double_compute_stats(testing_app_local_chunking_no_consistency):

    _, client = testing_app_local_chunking_no_consistency
    record_id = _create_record(client, "WellLog")
    _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20)),
                                                                        (['MD', 'X'], range(10, 30)),
                                                                        (['MD', 'X'], range(25, 40))])

    record_response = client.get(f'/ddms/v3/welllogs/{record_id}')
    assert record_response.status_code == 200
    version = record_response.json()['version']

    fetch_stats_for_3s(client, record_id)

    compute_stats_response = client.post(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics")
    assert compute_stats_response.status_code == 409


def test_get_stats(testing_app_local_chunking_no_consistency):
    _, client = testing_app_local_chunking_no_consistency

    record_id = _create_record(client, "WellLog")
    _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20)),
                                                                        (['MD', 'X'], range(10, 30)),
                                                                        (['MD', 'X'], range(25, 40))])

    fetch_stats_for_3s(client, record_id)

    record_response = client.get(f'/ddms/v3/welllogs/{record_id}')
    assert record_response.status_code == 200
    version = record_response.json()['version']

    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert get_stats_response.status_code == 200
    df_result_last_version = create_df_from_dict(get_stats_response)
    assert df_result_last_version.shape == (2, 9)

    get_stats_version_response = client.get(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics")
    assert get_stats_version_response.status_code == 200
    df_result_version = create_df_from_dict(get_stats_version_response)
    assert df_result_version.shape == (2, 9)

    params = {
        'curves': "MD,X"
    }
    get_stats_response_selected_cols = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response_selected_cols.status_code == 200
    df_result_selected_cols = create_df_from_dict(get_stats_response_selected_cols)
    assert df_result_selected_cols.shape == (2, 9)

    params = {
        'curves': "UnknownColumnName"
    }
    get_stats_response_unknown_cols = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    assert get_stats_response_unknown_cols.status_code == 404
    assert get_stats_response_unknown_cols.content == \
           b'{"errorType":"CURVES_NOT_FOUND","message":"Requested curves unknown"}'


def test_get_stats_from_not_computable_columns(testing_app_local_chunking_no_consistency):
    _, client = testing_app_local_chunking_no_consistency

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
    # params = {
    #     'curves': "bool-C,string-D"
    # }

    # todo: Update BulkStatistics class + swagger when only not computable columns are requested, 400 error is expected
    # get_stats_response_2 = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    # assert get_stats_response_2.status_code == 400


def test_get_stats_after_post_data(testing_app_local_chunking_no_consistency):
    
    _, client = testing_app_local_chunking_no_consistency
    record_id = _create_record(client, "WellLog")
    post_welllog_data(client, record_id, ['int-A', 'string-B', 'bool-C', 'string-D'], range(10))

    response = fetch_stats_for_3s(client, record_id)
    assert response.status_code == 200

    df_result_df = create_df_from_dict(response)
    assert df_result_df.shape == (1, 9)


@pytest.mark.parametrize("mode", ['chunking', 'all_at_once'])
def test_get_stats_meta_data(testing_app_local_chunking_no_consistency, mode):
    _, client = testing_app_local_chunking_no_consistency

    record_id = _create_record(client, "WellLog")
    if mode == 'chunking':
        _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20))])
    elif mode == 'all_at_once':
        post_welllog_data(client, record_id, ['MD', 'X'], range(20))

    fetch_stats_for_3s(client, record_id)

    record_response = client.get(f'/ddms/v3/welllogs/{record_id}')
    assert record_response.status_code == 200
    version = record_response.json()['version']

    get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
    assert get_stats_response.status_code == 200

    response_data = get_stats_response.json()
    assert response_data['recordId'] == record_id
    assert response_data['recordVersion'] == str(version)
    assert response_data['computationStatus'] == BulkStatisticsStatus.Complete


def test_get_stats_if_error(nope_logger_fixture, testing_app_local_chunking_no_consistency):

    async def _compute_stats_on_bulk_batch(n):
        if n % 2 == 0:
            raise Exception("test_get_stats_if_error")
    tasks = [asyncio.get_event_loop().create_task(_compute_stats_on_bulk_batch(i)) for i in range(5)]

    with mock.patch.object(BulkStatistics, 'trigger_stats_computation_in_dask') as bob:
        _, client = testing_app_local_chunking_no_consistency
        bob.return_value = tasks

        valid_record_id = _create_record(client, "WellLog")
        post_welllog_data(client, valid_record_id, ['int-A'], range(10))

        response = fetch_stats_for_3s(client, valid_record_id)
        assert response.status_code == 200

        response_data = response.json()
        assert response_data['computationStatus'] == BulkStatisticsStatus.Error


def test_compute_stats_on_legacy_welllog(testing_app_local_chunking_no_consistency):

    # Simulate the creation of a WellLog before Statistics features is available
    with mock.patch.object(BulkStatistics, 'compute_bulk_statistics', return_value=mock.AsyncMock()) as bob:
        _, client = testing_app_local_chunking_no_consistency

        record_id = _create_record(client, "WellLog")
        post_welllog_data(client, record_id, ['int-A', 'string-B', 'bool-C', 'string-D'], range(1000))

        asyncio.get_event_loop().run_until_complete(asyncio.sleep(2))
        get_stats_response = client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics')
        assert get_stats_response.text == '{"errorType":"DATA_NOT_FOUND","message":"Statistics do not exist"}'
        assert get_stats_response.status_code == 404

    record_response = client.get(f'/ddms/v3/welllogs/{record_id}')
    assert record_response.status_code == 200
    version = record_response.json()['version']

    # Then trigger computation manually at specific version
    compute_stats_response = client.post(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics")
    assert compute_stats_response.status_code == 200

    fetch_stats_for_3s(client, record_id)


# todo: add test case when using array data
def test_get_stats_array(testing_app_local_chunking_no_consistency):
    _, client = testing_app_local_chunking_no_consistency

    record_id = _create_record(client, "WellLog")
    array_cols = [f'ARRAY[{i}]' for i in range(10)]
    _create_chunks(client, 'WellLog', record_id=record_id, cols_ranges=[(array_cols, range(20))])

    response = fetch_stats_for_3s(client, record_id, columns=['ARRAY'])
    assert response.status_code == 200


def test_trigger_computations_after_error(testing_app_local_chunking_no_consistency):
    pass



# todo: check response with those data
#  columns = ['int-A', 'int-A-with-nan', 'float-B', 'float-B-with-nan',
#  'bool-D', 'string-E', 'date-C', 'date-C-with-nan']