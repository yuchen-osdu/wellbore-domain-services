import anyio
from typing import List
from httpx import AsyncClient
from aiohttp import ClientSession
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from natsort import natsorted

import pytest
from unittest.mock import patch, AsyncMock

from tests.unit.generate_data import generate_df
from tests.unit.routers.chunking_test import (
    Definitions,
    _create_chunks,
    _create_record,
)
from app.context import Context
from unittest.mock import Mock

from app.bulk_persistence import BulkIOWdmsWorker
from app.bulk_persistence.errors import BulkWorkerError

from app.routers.bulk.bulk_routes_dependencies import get_bulk_id_access

pytestmark = [pytest.mark.statistics]


async def post_record_data(client: AsyncClient, partition_header: dict, record_id: str, entity_type: str, columns: List[str], range_index: range):
    headers = {'content-type': 'application/x-parquet', **partition_header}
    chunking_url = Definitions[entity_type]["chunking_url"]

    data_df = generate_df(columns, range_index)
    cols_with_nan = [c for c in data_df.columns if c.endswith('nan')]
    for col_with_nan in cols_with_nan:
        data_df.loc[data_df.sample(frac=0.1).index, col_with_nan] = np.nan

    data_to_send = data_df.to_parquet(engine='pyarrow')

    write_response = await client.post(f'{chunking_url}/{record_id}/data', data=data_to_send, headers=headers)
    assert write_response.status_code == 200
    return write_response


def create_df_from_dict(response):
    dict_data = response.json()['data']
    return pd.DataFrame.from_dict(dict_data, orient='index')


async def fetch_stats_for_3s(client: AsyncClient, header, record_id, *, columns=None, timeout=3, assert_if_failed=True):
    """
    Try to get statistics several times until the timeout is reached for given record id with given columns
    """

    api_results = []
    sleep_duration = 0.1
    # at the minimum timeout must be equals to sleep_duration
    timeout = max(sleep_duration, timeout)

    params = None
    if columns:
        params = {
            "curves": ",".join(columns)
        }

    attempts = int(timeout / sleep_duration)
    for i in range(attempts):
        get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                              params=params, headers=header)
        api_results.append(get_stats_response)
        if get_stats_response.status_code != 404:
            break

        await anyio.sleep(sleep_duration)

    successful_response = [r for r in api_results if r.status_code == 200]
    faulty_responses = [r for r in api_results if r.status_code != 200]
    if assert_if_failed:
        assert successful_response, faulty_responses if faulty_responses else ""
    return successful_response[0] if successful_response else faulty_responses[0]


@pytest.mark.anyio
async def test_invalid_cases(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency
    header = local_partition_header
    valid_record_id = await _create_record(client, entity_type='WellLog', header=header)

    version = '123456789'
    unknown_record_id = 'test:work-product-component--WellLog:8fef694e8a5a49ec96db9e51c7522bc9'

    get_stats_response = await client.get(f'/ddms/v3/welllogs/{unknown_record_id}/data/statistics',
                                          headers=header)
    assert get_stats_response.status_code == 404
    assert get_stats_response.json().get('origin') == "osdu-data-ecosystem-storage"

    post_stats_response = await client.post(f"/ddms/v3/welllogs/{unknown_record_id}/versions/{version}/data/statistics",
                                            headers=header)
    assert post_stats_response.status_code == 404
    assert post_stats_response.json().get('origin') == "osdu-data-ecosystem-storage"

    valid_record_no_bulk_response = await client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics',
                                                     headers=header)
    assert valid_record_no_bulk_response.status_code == 404
    assert valid_record_no_bulk_response.json().get("detail") == f"bulk for record {valid_record_id} not found"

    valid_record_invalid_version_response = await client.get(
        f"/ddms/v3/welllogs/{valid_record_id}/versions/{version}/data/statistics",
        headers=header)
    assert valid_record_invalid_version_response.status_code == 404
    assert valid_record_invalid_version_response.json().get('origin') == "osdu-data-ecosystem-storage"


@pytest.mark.anyio
async def test_with_bulk_no_stats(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency
    header = local_partition_header

    valid_record_id = await _create_record(client, 'WellLog', header=header)
    await post_record_data(client, header, valid_record_id, 'WellLog', ['int-A'], range(10))

    valid_record_with_bulk_response = await client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics', headers=header)
    assert valid_record_with_bulk_response.status_code == 404
    assert valid_record_with_bulk_response.content == b'{"errorType":"DATA_NOT_FOUND","message":"Statistics do not exist"}'


@pytest.mark.skip
@pytest.mark.anyio
async def test_get_stats_with_worker(testing_app_local_chunking_no_consistency):

    with patch.object(ClientSession, 'get', return_value=AsyncMock(name="clientSession_get")) as get_statistics_mock:
        get_statistics_mock.return_value.__aenter__.return_value.status = 200
        get_statistics_mock.return_value.__aenter__.return_value.read.return_value = b'mock raw bytes'

        app, client = testing_app_local_chunking_no_consistency
        valid_record_id = await _create_record(client, 'WellLog')

        # to skip `if not bulk_uri.is_valid():` condition in get_statistics router
        m = Mock(name='get_bulk_id_access', return_value=1)
        m.get_bulk_uri.return_value.is_valid.return_value = True
        m.get_bulk_uri.return_value.bulk_id = "bob_uri"
        app.dependency_overrides[get_bulk_id_access] = lambda: m

        await client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics', params={"curves": "A,B,C"})
        get_statistics_mock.assert_called_once()

        _args, _kwargs = get_statistics_mock.call_args
        assert sorted(_kwargs["headers"].keys()) == sorted(
            ["Authorization", "correlation-id", "traceparent"]
        )
        assert _kwargs["params"] == {"curves_selection": ["A", "B", "C"]}
        assert _args[0].startswith(f"worker_host/data/{valid_record_id}/")


@pytest.mark.skip
@pytest.mark.anyio
async def test_post_stats_with_worker(testing_app_local_chunking_no_consistency):

    with patch.object(ClientSession, 'post', return_value=AsyncMock(name="post")) as post_statistics_mock:
        post_statistics_mock.return_value.__aenter__.return_value.status = 209
        post_statistics_mock.return_value.__aenter__.return_value.read.return_value = b'raw bytes'

        app, client = testing_app_local_chunking_no_consistency
        valid_record_id, record_version = await _create_record(client, 'WellLog', return_version=True)

        # to skip `if not bulk_uri.is_valid():` condition in get_statistics router
        m = Mock(name='get_bulk_id_access', return_value=1)
        m.get_bulk_uri.return_value.is_valid.return_value = True
        m.get_bulk_uri.return_value.bulk_id = "bob_uri"
        app.dependency_overrides[get_bulk_id_access] = lambda: m

        compute_stats_response = await client.post(f"/ddms/v3/welllogs/{valid_record_id}/versions/{record_version}/data/statistics")

        assert compute_stats_response.status_code == 209 # choose arbitrary code to ensure status code is returned
        post_statistics_mock.assert_called_once()
        _args, _kwargs = post_statistics_mock.call_args
        assert sorted(_kwargs["headers"].keys()) == sorted(
            ["Authorization", "correlation-id", "traceparent"]
        )
        assert _args[0] == f"worker_host/data/{valid_record_id}/bob_uri/statistics"


def _prepare_mock():
    async_mock = AsyncMock(ClientSession, name="http_session_mock")
    async_mock.get.return_value.__aenter__.return_value.status = 400
    async_mock.get.return_value.__aenter__.return_value.read.return_value = b'mock raw bytes'
    async_mock.post.return_value.__aenter__.return_value.status = 400
    async_mock.post.return_value.__aenter__.return_value.read.return_value = b'mock raw bytes'
    async_mock.post.return_value.__aenter__.return_value.text.return_value = b'mock raw bytes'

    return async_mock


@pytest.mark.skip
@pytest.mark.anyio
async def test_verify_stats_headers():

    created_ctx = Context(**{
        "correlation_id": 'my-correlation-id',
        "request_id": 'my-request-id',
        "auth": 'my-auth',
        "partition_id": 'my-partition-id',
        "x_user_id": 'my-x-user-id',
        "x_app_id": "my-x-app-id",
    })
    expected_headers = ["Authorization", "data-partition-id",  "correlation-id", "x-user-id", "x-app-id"]

    async_mock = _prepare_mock()
    bulk_io_worker = BulkIOWdmsWorker(Mock(), async_mock)

    await bulk_io_worker.get_statistics(created_ctx, Mock(), Mock(), Mock())
    _, _kwargs = async_mock.get.call_args
    assert set(expected_headers).issubset(set(_kwargs["headers"].keys()))

    await bulk_io_worker.post_statistics(created_ctx, Mock(), Mock(), Mock())
    _, _kwargs = async_mock.post.call_args
    assert set(expected_headers).issubset(set(_kwargs["headers"].keys()))

    with pytest.raises(BulkWorkerError):
        await bulk_io_worker.write_bulk(created_ctx, b'some bytes', Mock(), Mock(), Mock(), Mock())
    _, _kwargs = async_mock.post.call_args
    assert {*expected_headers, "Content-Type"}.issubset(set(_kwargs["headers"].keys()))

    with pytest.raises(BulkWorkerError):
        await bulk_io_worker.read_data(created_ctx, Mock(), Mock(), Mock(), Mock(), Mock())
    _, _kwargs = async_mock.get.call_args
    assert {*expected_headers, "accept"}.issubset(set(_kwargs["headers"].keys()))


@pytest.mark.anyio
async def test_with_bulk_stats_not_complete(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency
    header = local_partition_header
    valid_record_id = await _create_record(client, 'WellLog', header=header)

    await post_record_data(client, header, valid_record_id, 'WellLog', ['int-A'], range(10))

    valid_record_with_bulk_response = await client.get(f'/ddms/v3/welllogs/{valid_record_id}/data/statistics',
                                                       headers=header)
    assert valid_record_with_bulk_response.status_code == 404
    assert valid_record_with_bulk_response.content \
               == b'{"errorType":"DATA_NOT_FOUND","message":"Statistics do not exist"}'


async def _trigger_computation_on_record(client, header, record_id, record_version):
    """ Trigger computation of bulk statistics for given record id at given record_version or last version if None """

    if not record_version:
        record_response = await client.get(f'/ddms/v3/welllogs/{record_id}', headers=header)
        assert record_response.status_code == 200
        record_version = record_response.json()['version']

    return await client.post(f"/ddms/v3/welllogs/{record_id}/versions/{record_version}/data/statistics",
                             headers=header)


@pytest.mark.anyio
async def test_double_compute_stats(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency
    record_id = await _create_record(client, 'WellLog', local_partition_header)
    await _create_chunks(client, local_partition_header,
                         'WellLog', record_id=record_id,
                         cols_ranges=[(['MD', 'X'], range(20)),
                                      (['MD', 'X'], range(10, 30)),
                                      (['MD', 'X'], range(25, 40))])

    record_response = await client.get(f'/ddms/v3/welllogs/{record_id}', headers=local_partition_header)
    assert record_response.status_code == 200
    version = record_response.json()['version']

    computation_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                record_id, record_version=version)
    assert computation_response.status_code == 200

    await fetch_stats_for_3s(client, local_partition_header, record_id)

    compute_stats_response = await _trigger_computation_on_record(client,local_partition_header,
                                                                  record_id, record_version=version)
    assert compute_stats_response.status_code == 409
    assert compute_stats_response.json()['detail'] == "Statistics computation already complete"


@pytest.mark.anyio
async def test_get_stats(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency

    columns = ['int-A', 'int-A-with-nan', 'float-B', 'float-B-with-nan', 'date-C', 'date-C-with-nan']
    record_id = await _create_record(client, 'WellLog', local_partition_header)
    await post_record_data(client, local_partition_header, record_id, 'WellLog', columns, range(1000))

    computation_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                record_id, record_version=None)
    assert computation_response.status_code == 200

    await fetch_stats_for_3s(client, local_partition_header, record_id)

    record_response = await client.get(f'/ddms/v3/welllogs/{record_id}', headers=local_partition_header)
    assert record_response.status_code == 200
    version = record_response.json()['version']

    get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', headers=local_partition_header)
    assert get_stats_response.status_code == 200
    df_result_last_version = create_df_from_dict(get_stats_response)
    assert df_result_last_version.shape == (len(columns), 9)

    get_stats_version_response = await client.get(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics",
                                                  headers=local_partition_header)
    assert get_stats_version_response.status_code == 200
    df_result_version = create_df_from_dict(get_stats_version_response)
    assert df_result_version.shape == (len(columns), 9)

    sub_columns = ['int-A-with-nan', 'float-B', 'float-B-with-nan', 'date-C']
    params = {
        'curves': ','.join(sub_columns)
    }
    get_stats_response_selected_cols = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                                        params=params, headers=local_partition_header)
    assert get_stats_response_selected_cols.status_code == 200
    df_result_selected_cols = create_df_from_dict(get_stats_response_selected_cols)
    assert df_result_selected_cols.shape == (len(sub_columns), 9)

    params = {
        'curves': "UnknownColumnName"
    }
    get_stats_response_unknown_cols = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                                       params=params, headers=local_partition_header)
    assert get_stats_response_unknown_cols.status_code == 404
    assert get_stats_response_unknown_cols.content == \
           b'{"errorType":"CURVES_NOT_FOUND","message":"Requested curves unknown"}'


@pytest.mark.anyio
async def test_get_stats_from_not_computable_columns(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency

    record_id = await _create_record(client, 'WellLog', local_partition_header)
    await _create_chunks(client, local_partition_header,
                         'WellLog',
                         record_id=record_id,
                         cols_ranges=[(['int-A', 'string-B', 'bool-C', 'string-D'], range(20))])

    computation_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                record_id, record_version=None)
    assert computation_response.status_code == 200
    await fetch_stats_for_3s(client, local_partition_header, record_id)

    # not computable curves + unknown curves requested => 404
    params = {
        'curves': "bool-D,string-E,UnknownColumn"
    }
    get_stats_response_1 = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                            params=params, headers=local_partition_header)
    assert get_stats_response_1.status_code == 404

    # not computable curves requested => 400
    # params = {
    #     'curves': "bool-C,string-D"
    # }

    # todo: Update BulkStatistics class + swagger when only not computable columns are requested, 400 error is expected
    # get_stats_response_2 = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', params=params)
    # assert get_stats_response_2.status_code == 400


@pytest.mark.anyio
async def test_get_stats_after_post_data(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency
    record_id = await _create_record(client, 'WellLog', local_partition_header)
    await post_record_data(client, local_partition_header, record_id, 'WellLog', ['int-A', 'string-B', 'bool-C', 'string-D'], range(10))

    computation_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                record_id, record_version=None)
    assert computation_response.status_code == 200

    response = await fetch_stats_for_3s(client, local_partition_header, record_id)
    assert response.status_code == 200

    df_result_df = create_df_from_dict(response)
    assert df_result_df.shape == (1, 9)


@pytest.mark.parametrize("mode", ['chunking', 'all_at_once'])
@pytest.mark.anyio
async def test_get_stats_meta_data(testing_app_local_chunking_no_consistency, mode, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency

    record_id = await _create_record(client, 'WellLog', local_partition_header)
    if mode == 'chunking':
        await _create_chunks(client, local_partition_header,
                             'WellLog', record_id=record_id, cols_ranges=[(['MD', 'X'], range(20))])
    elif mode == 'all_at_once':
        await post_record_data(client,local_partition_header,
                               record_id, 'WellLog', ['MD', 'X'], range(20))

    record_response = await client.get(f'/ddms/v3/welllogs/{record_id}',
                                       headers=local_partition_header)
    assert record_response.status_code == 200
    version = record_response.json()['version']

    computation_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                record_id, version)
    assert computation_response.status_code == 200
    await fetch_stats_for_3s(client, local_partition_header, record_id)

    get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                          headers=local_partition_header)
    assert get_stats_response.status_code == 200

    response_data = get_stats_response.json()
    assert response_data['recordId'] == record_id
    assert response_data['recordVersion'] == version
    assert response_data['computationStatus'] == 'complete'

    now = datetime.now(timezone.utc)
    retrieved_datetime = datetime.fromisoformat(response_data['computationStartDatetime'])
    assert now - timedelta(seconds=3) < retrieved_datetime < now + timedelta(seconds=3)


@pytest.mark.anyio
async def test_get_stats_if_error(nope_logger_fixture, testing_app_local_chunking_no_consistency, local_partition_header):
    async def _compute_stats_on_bulk_batch(n):
        if n % 2 == 0:
            raise Exception("test_get_stats_if_error")

    tasks = [_compute_stats_on_bulk_batch(i) for i in range(5)]

    _, client = testing_app_local_chunking_no_consistency

    valid_record_id = await _create_record(client, 'WellLog', local_partition_header)
    await post_record_data(client, local_partition_header,
                           valid_record_id, 'WellLog', ['int-A'], range(10))
    computation_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                valid_record_id, record_version=None)
    assert computation_response.status_code == 200

    response = await fetch_stats_for_3s(client, local_partition_header, valid_record_id)
    assert response.status_code == 200

    response_data = response.json()
    assert response_data['computationStatus'] == 'complete'


@pytest.mark.anyio
async def test_compute_stats_on_legacy_welllog(testing_app_local_chunking_no_consistency, local_partition_header):
    # Simulate the creation of a WellLog before Statistics features is available
    _, client = testing_app_local_chunking_no_consistency

    record_id = await _create_record(client, 'WellLog', header=local_partition_header)
    await post_record_data(client, local_partition_header, record_id, 'WellLog', ['int-A', 'string-B', 'bool-C', 'string-D'], range(1000))

    # TODO uncomment when automatic stat computation is enabled again
    #await anyio.sleep(2)

    get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics', headers=local_partition_header)
    assert get_stats_response.text == '{"errorType":"DATA_NOT_FOUND","message":"Statistics do not exist"}'
    assert get_stats_response.status_code == 404

    record_response = await client.get(f'/ddms/v3/welllogs/{record_id}', headers=local_partition_header)
    assert record_response.status_code == 200
    version = record_response.json()['version']

    # Then trigger computation manually at specific version
    compute_stats_response = await client.post(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics",
                                               headers=local_partition_header)
    assert compute_stats_response.status_code == 200

    await fetch_stats_for_3s(client, local_partition_header, record_id)


@pytest.mark.skip(reason="Tests with Dask are skipped.")
@pytest.mark.anyio
async def test_trigger_computations_after_n_error(testing_app_local_chunking_no_consistency, local_partition_header):
    async def _compute_stats_on_bulk_batch():
        raise Exception("test_get_stats_if_error")

    task = _compute_stats_on_bulk_batch()

    computation_retry_attempts = 3

    _, client = testing_app_local_chunking_no_consistency

    record_id = await _create_record(client, 'WellLog', local_partition_header)
    await post_record_data(client, local_partition_header,
                           record_id, 'WellLog', ['int-A'], range(10))
    computation_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                record_id, record_version=None)
    assert computation_response.status_code == 200

    get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                          headers=local_partition_header)
    assert get_stats_response.status_code == 200
    assert get_stats_response.json()['computationStatus'] == 'complete'

    record_response = await client.get(f'/ddms/v3/welllogs/{record_id}',
                                       headers=local_partition_header)
    version = record_response.json()['version']

    # one try is already done after posting data "await post_record_data(client, record_id, ['int-A'], range(10))"
    for i in range(computation_retry_attempts - 1):
        compute_stats_response = await client.post(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics",
                                                   headers=local_partition_header)
        assert compute_stats_response.status_code == 200

        get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                              headers=local_partition_header)
        assert get_stats_response.status_code == 200
        assert get_stats_response.json()['computationStatus'] == 'error'

    compute_stats_response = await client.post(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics",
                                               headers=local_partition_header)
    assert compute_stats_response.status_code == 409, \
        f"After '{computation_retry_attempts}' retries, 409 should be returned"


@pytest.mark.skip(reason="Tests with Dask are skipped.")
@pytest.mark.anyio
async def test_trigger_computations_after_duration(testing_app_local_chunking_no_consistency, local_partition_header):
        _, client = testing_app_local_chunking_no_consistency

        record_id = await _create_record(client, 'WellLog', local_partition_header)
        await post_record_data(client, local_partition_header,
                               record_id, 'WellLog', ['int-A'], range(10))

        with pytest.raises(RuntimeError):
            await _trigger_computation_on_record(client, local_partition_header,
                                                 record_id, record_version=None)

        # so stats data are not available
        get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                              headers=local_partition_header)
        assert get_stats_response.status_code == 404
        assert get_stats_response.content == b'{"errorType":"COMPUTATION_NOT_COMPLETE",' \
                                             b'"message":"Statistics computation not finished yet"}'

        record_response = await client.get(f'/ddms/v3/welllogs/{record_id}',
                                           headers=local_partition_header)
        version = record_response.json()['version']

        # Try to trigger computation several times, but `_duration_before_recompute` is not past yet => 409
        for i in range(4):
            compute_stats_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                          record_id, version)
            assert compute_stats_response.status_code == 409

            get_stats_response = await client.get(f'/ddms/v3/welllogs/{record_id}/data/statistics',
                                                  headers=local_partition_header)
            assert get_stats_response.status_code == 404
            assert get_stats_response.content == b'{"errorType":"COMPUTATION_NOT_COMPLETE",' \
                                                 b'"message":"Statistics computation not finished yet"}'

        # update on the fly the value of expected duration before re-computation, to simulate time is up
        compute_stats_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                      record_id, version)
        assert compute_stats_response.status_code == 200


@pytest.mark.anyio
async def test_get_stats_array(testing_app_local_chunking_no_consistency, local_partition_header):
    _, client = testing_app_local_chunking_no_consistency

    record_id = await _create_record(client, 'WellLog', header=local_partition_header)
    array_cols = [f'ARRAY[{i}]' for i in range(10)]
    await _create_chunks(client, local_partition_header,
                         'WellLog', record_id=record_id, cols_ranges=[(array_cols, range(20))])

    compute_stats_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                  record_id, record_version=None)
    assert compute_stats_response.status_code == 200

    response = await fetch_stats_for_3s(client, local_partition_header, record_id, columns=['ARRAY'])
    assert response.status_code == 200
    df_result_df = create_df_from_dict(response)
    assert df_result_df.shape == (10, 9)


@pytest.mark.skip(reason="Tests with Dask are skipped.")
@pytest.mark.anyio
async def test_stats_data_duplication_after_re_computation(testing_app_local_chunking_no_consistency, local_partition_header):
        _, client = testing_app_local_chunking_no_consistency

        record_id = await _create_record(client, 'WellLog', local_partition_header)
        columns = [f'ARRAY[{i}]' for i in range(100)]
        await post_record_data(client, local_partition_header, record_id, 'WellLog', columns, range(100))
        compute_stats_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                      record_id, record_version=None)
        assert compute_stats_response.status_code == 200

        get_stats_response = await fetch_stats_for_3s(client, local_partition_header, record_id)
        df_result_df = create_df_from_dict(get_stats_response)
        assert df_result_df.shape == (len(columns), 9)
        assert natsorted(list(df_result_df.index)) == columns

        record_response = await client.get(f'/ddms/v3/welllogs/{record_id}', headers=local_partition_header)
        version = record_response.json()['version']

        # remove check to trigger again the computation
        recompute_stats_response = await _trigger_computation_on_record(client, local_partition_header,
                                                                        record_id, record_version=version)
        assert recompute_stats_response.status_code == 200

        response = await fetch_stats_for_3s(client, local_partition_header, record_id)
        assert response.status_code == 200
        result_df = create_df_from_dict(response)
        assert result_df.shape == (len(columns), 9)
        assert natsorted(list(df_result_df.index)) == columns


@pytest.mark.parametrize("mode", ['chunking', 'all_at_once'])
@pytest.mark.parametrize("entity_type", [
    "WellboreTrajectory"
])
@pytest.mark.anyio
async def test_stats_available_welllog_only_on_bulk_creation(testing_app_local_chunking_no_consistency, local_partition_header,
                                                             mode, entity_type):
    _, client = testing_app_local_chunking_no_consistency
    record_id = await _create_record(client, entity_type, local_partition_header)
    if mode == 'chunking':
        await _create_chunks(client, local_partition_header,
                             entity_type, record_id=record_id, cols_ranges=[(['MD', 'X'], range(20))])
    elif mode == 'all_at_once':
        await post_record_data(client, local_partition_header,
                               record_id, entity_type, ['MD', 'X'], range(20))

    get_stats_response = await fetch_stats_for_3s(client, local_partition_header,
                                                  record_id, assert_if_failed=False)
    assert get_stats_response.status_code == 422


@pytest.mark.parametrize("entity_type", ["WellboreTrajectory"])
@pytest.mark.anyio
async def test_stats_available_welllog_only_on_existing_record(testing_app_local_chunking_no_consistency,
                                                               local_partition_header,
                                                               entity_type):
    _, client = testing_app_local_chunking_no_consistency

    record_id = await _create_record(client, entity_type, local_partition_header)
    await post_record_data(client, local_partition_header, record_id, entity_type, ['MD', 'X'], range(20))

    get_stats_response = await fetch_stats_for_3s(client, local_partition_header, record_id, assert_if_failed=False)
    assert get_stats_response.status_code == 422

    entity_url = Definitions[entity_type]['base_url']
    record_response = await client.get(f'{entity_url}/{record_id}', headers=local_partition_header)
    assert record_response.status_code == 200
    version = record_response.json()['version']

    compute_stats_response = await client.post(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics",
                                               headers=local_partition_header)
    assert compute_stats_response.status_code == 422


@pytest.mark.anyio
async def test_invalid_bulk_uri_cases(testing_app_local_chunking_no_consistency, local_partition_header):

    with patch('app.bulk_persistence.bulk_uri.BulkURI.is_valid', return_value=False):
        _, client = testing_app_local_chunking_no_consistency
        record_id = await _create_record(client, 'WellLog', local_partition_header)

        record_response = await client.get(f'/ddms/v3/welllogs/{record_id}', headers=local_partition_header)
        assert record_response.status_code == 200
        version = record_response.json()['version']

        compute_stats_response = await client.post(f"/ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics",
                                                   headers=local_partition_header)
        assert compute_stats_response.status_code == 422
        assert compute_stats_response.json() == {"detail": "Record contains an invalid bulk URI"}
