import io
import math
import platform

import numpy as np
import pandas as pd
import pandas.api.types as ptypes
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from pandas.testing import assert_frame_equal
from tests.unit.persistence.dask_blob_storage_test import generate_df


Definitions = {
    'WellLog': {
        'api_version': 'v3',
        'base_url': '/ddms/v3/welllogs',
        'chunking_url': '/ddms/v3/welllogs',
        'kind': 'osdu:wks:work-product-component--WellLog:1.1.0',
        'record_data': {
            "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "Curves": [{"CurveID": "MD"}, {"CurveID": "X"}],
            "ExtensionProperties": {"my_test_extension": 42},
        }
    },

    'WellboreTrajectory': {
        'api_version': 'v3',
        'base_url': '/ddms/v3/wellboretrajectories',
        'chunking_url': '/ddms/v3/wellboretrajectories',
        'kind': 'osdu:wks:work-product-component--WellboreTrajectory:1.0.0',
        'record_data': {
            "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "TopDepthMeasuredDepth": 12345.6,
            "BaseDepthMeasuredDepth": 12345.6,
            "VerticalMeasurement": {"VerticalMeasurement": 12345.6}
        }
    },
    'Log': {
        'api_version': 'v2',
        'base_url': '/ddms/v2/logs',
        'chunking_url': '/alpha/ddms/v2/logs',
        'kind': 'osdu:wks:log:1.0.5',
        'record_data': {
            "name": "myLog_name"
        }
    }
}

EntityTypeParams = ['WellLog', 'WellboreTrajectory', 'Log']


def _create_df_from_response(response):
    f = io.BytesIO(response.content)
    f.seek(0)

    content_type = response.headers.get('content-type')
    if content_type == 'application/x-parquet':
        return pd.read_parquet(f)
    elif content_type == 'application/json':
        return pd.read_json(f, dtype=True, orient='split', convert_axes=False).replace("NaN", np.NaN)
    else:
        raise ValueError(f"Unknown content-type: '{content_type}'")


def _df_to_format(df, data_format):
    if data_format == 'parquet':
        return df.to_parquet(engine="pyarrow")
    elif data_format == 'json':
        return df.to_json(orient='split', date_format='iso')
    else:
        raise ValueError(f"Unknown content-type: '{data_format}'")


def _create_record(client, entity_type):
    entity_def = Definitions[entity_type]
    create_url = entity_def['base_url']
    kind = entity_def['kind']
    record_data = entity_def['record_data']

    record = {
        "kind": kind,
        "acl": {
            "viewers": ["data.default.viewers@opendes.enterprisedata.cloud.slb-ds.com"],
            "owners": ["data.default.owners@opendes.enterprisedata.cloud.slb-ds.com"]
        },
        "legal": {
            "legaltags": ["opendes-storage-1602183747123"],
            "otherRelevantDataCountries": ["US"],
        },
        'version': 0,
        "data": record_data
    }
    response = client.post(create_url, json=[record])
    assert response.status_code == 200
    record_id = response.json()["recordIds"][0]
    return record_id


def _cast_datetime_to_datetime64_ns(result_df):
    """  if datetime is detected, cast data column as datetime to ensure date values are valid  """
    for name, _col in result_df.items():
        if name.startswith('date'):
            result_df[name] = result_df[name].astype('datetime64[ns]')

    return result_df


@pytest.fixture()
def dasked_test_app_without_consistency_client(testing_app_local_chunking_no_consistency):
    _, client = testing_app_local_chunking_no_consistency
    yield client


def test_post_data_merge_extension_properties(dasked_test_app_without_consistency_client):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, "WellLog")
    chunking_url = Definitions["WellLog"]['chunking_url']

    df = generate_df(['MD'], range(10))
    data_to_send = df.to_json(orient='split', date_format='iso')
    headers = {'content-type': 'application/json'}

    write_response = client.post(f'{chunking_url}/{record_id}/data', data=data_to_send, headers=headers)
    assert write_response.status_code == 200

    get_response = client.get(f'{chunking_url}/{record_id}')
    assert get_response.status_code == 200

    expected = Definitions["WellLog"]["record_data"]["ExtensionProperties"].copy()

    expected["wdms"] = get_response.json()["data"]["ExtensionProperties"]["wdms"]

    assert get_response.json()["data"]["ExtensionProperties"] == expected


@pytest.mark.parametrize("entity_type", EntityTypeParams)
@pytest.mark.parametrize("content_type_header,create_func", [
    ('application/x-parquet', lambda df: df.to_parquet(engine="pyarrow")),
    ('application/json', lambda df: df.to_json(orient='split', date_format='iso')),
])
@pytest.mark.parametrize("accept_content", [
    'application/x-parquet',
    'application/json',
])
@pytest.mark.parametrize("columns", [
    ['MD', 'X'],
    ['float_MD', 'float_X'],
    ['str_MD', 'str_X'],
    ['date_MD', 'date_X'],
    ['MD', 'date_X', 'float_X', 'str_X']
])
def test_send_all_data_once(dasked_test_app_without_consistency_client,
                            entity_type,
                            columns,
                            content_type_header,
                            create_func,
                            accept_content):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    initial_data_df = generate_df(columns, range(5, 13))
    data_to_send = create_func(initial_data_df)
    headers = {'content-type': content_type_header}

    get_response_no_data = client.get(f'{chunking_url}/{record_id}/data', headers=headers)
    assert get_response_no_data.status_code == 404

    write_response = client.post(f'{chunking_url}/{record_id}/data', data=data_to_send, headers=headers)
    assert write_response.status_code == 200

    get_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': accept_content})
    assert get_response.status_code == 200
    result_df = _create_df_from_response(get_response)

    if content_type_header.endswith('parquet') and not accept_content.endswith('parquet'):
        result_df = _cast_datetime_to_datetime64_ns(result_df)

    if content_type_header.endswith('json'):
        initial_data_df = pd.read_json(data_to_send, orient='split')

    assert initial_data_df.index.dtype == result_df.index.dtype
    assert initial_data_df.shape == result_df.shape
    pd.testing.assert_frame_equal(initial_data_df, result_df,
                                  check_dtype=False,
                                  check_column_type=False,
                                  check_datetimelike_compat=True,
                                  )


@pytest.mark.parametrize("entity_type",
                         [entity for entity in EntityTypeParams if Definitions[entity]['api_version'] == "v2"])
@pytest.mark.parametrize("content_type_header,create_func", [
    ('application/json', lambda df: df.to_json(orient='split', date_format='iso')),
])
@pytest.mark.parametrize("accept_content", [
    'application/json',
])
@pytest.mark.parametrize("columns", [
    ['MD', 'X'],
    ['float_MD', 'float_X'],
    ['str_MD', 'str_X'],
    ['date_MD', 'date_X'],
    ['MD', 'date_X', 'float_X', 'str_X']
])
def test_send_all_data_once_post_data_v2_get_data_v3(dasked_test_app_without_consistency_client,
                                                     entity_type,
                                                     columns,
                                                     content_type_header,
                                                     create_func,
                                                     accept_content):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']
    base_url = Definitions[entity_type]['base_url']

    initial_data_df = generate_df(columns, range(5, 13))
    data_to_send = create_func(initial_data_df)
    headers = {'content-type': content_type_header}

    get_response_no_data = client.get(f'{chunking_url}/{record_id}/data', headers=headers)
    assert get_response_no_data.status_code == 404

    write_response = client.post(f'{base_url}/{record_id}/data', data=data_to_send, headers=headers)
    assert write_response.status_code == 200

    get_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': accept_content})
    assert get_response.status_code == 200
    result_df = _create_df_from_response(get_response)

    if content_type_header.endswith('json'):
        initial_data_df = pd.read_json(data_to_send, orient='split')

    assert initial_data_df.index.dtype == result_df.index.dtype
    assert initial_data_df.shape == result_df.shape
    pd.testing.assert_frame_equal(initial_data_df, result_df,
                                  check_dtype=False,
                                  check_column_type=False,
                                  check_datetimelike_compat=True,
                                  )


@pytest.mark.parametrize("entity_type", EntityTypeParams)
@pytest.mark.parametrize("content_type_header, create_func", [
    ('application/x-parquet', lambda df: df.to_parquet(engine="pyarrow")),
    ('application/json', lambda df: df.to_json(orient='split', date_format='iso')),
])
@pytest.mark.parametrize("accept_content", [
    'application/x-parquet',
    'application/json',
])
@pytest.mark.parametrize("columns", [
    ['float_MD', 'float_X'],
    ['str_MD', 'str_X'],
    ['date_MD', 'date_X'],
    ['TVD', 'float_X', 'str_X', 'date_X'],
    ['MD', 'X'],
    ['MD', 'float_X'],
    ['MD', 'str_MD'],

    # BELOW test cases FAIL with UPDATE mode:
    # => If adding new column Date/String not starting at first index AND override an existing column
    # ['MD', 'date_X'],
    # ['MD', 'float_X', 'str_X', 'date_X'],
])
@pytest.mark.parametrize("session_mode", [
    'overwrite',
    'update',
])
def test_overwrite_data_by_chunk_append(dasked_test_app_without_consistency_client, entity_type, columns,
                                        content_type_header, create_func,
                                        accept_content, session_mode):
    """ Create session, append chunking with consecutive index, validate session """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    initial_df = generate_df(['MD', 'X'], range(5))
    write_response = client.post(f'{chunking_url}/{record_id}/data',
                                 data=initial_df.to_json(orient='split', date_format='iso'),
                                 headers={'Content-Type': 'application/json'})

    assert write_response.status_code == 200
    get_response = client.get(f'{chunking_url}/{record_id}/data')
    assert get_response.status_code == 200
    initial_bulk_data = _create_df_from_response(get_response)
    assert initial_bulk_data.shape == initial_df.shape, "existing bulk data should not be empty"

    data_format = 'json' if content_type_header.endswith('json') else 'parquet'
    chunk_dfs = _create_chunks(client, entity_type, record_id=record_id, session_mode=session_mode,
                               data_format=data_format,
                               cols_ranges=[(columns, range(5, 10)),
                                            (columns, range(10, 15))])

    get_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': accept_content})
    assert get_response.status_code == 200
    df = _create_df_from_response(get_response)

    if session_mode == 'update':
        chunk_dfs.insert(0, initial_df)

    expected = pd.concat(chunk_dfs, axis=0)
    df = _cast_datetime_to_datetime64_ns(df)

    sorted_columns = sorted(columns)
    df = df[sorted_columns]
    expected = expected[sorted_columns]
    pd.testing.assert_frame_equal(df, expected,
                                  check_dtype=False,
                                  check_column_type=False,
                                  check_datetimelike_compat=True,
                                  )


def _send_chunk(client, url, chunk_df, data_format):
    if data_format == 'json':
        headers = {'Content-Type': 'application/json'}
    elif data_format == 'parquet':
        headers = {'content-type': 'application/x-parquet'}
    else:
        raise ValueError(f"Unknown content-type: '{data_format}'")

    chunk_response = client.post(url, data=_df_to_format(chunk_df, data_format), headers=headers)
    assert chunk_response.status_code == 200


def _create_chunks(client, entity_type, cols_ranges, record_id, session_mode='update', data_format='json'):
    """ Create session, add chunks with given columns and index, validate the session """

    chunking_url = Definitions[entity_type]["chunking_url"]
    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': session_mode})
    assert session_response.status_code == 200
    session_data = session_response.json()
    assert 'id' in session_data
    session_id = session_data['id']
    created_dfs = []

    for columns, ranges in cols_ranges:
        chunk_df = generate_df(columns, ranges)
        created_dfs.append(chunk_df)

        _send_chunk(client, f'{chunking_url}/{record_id}/sessions/{session_id}/data', chunk_df, data_format)

    commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert commit_response.status_code == 200
    assert commit_response.json()['state'] == SessionState.Committed
    assert commit_response.json()['version']
    return created_dfs


@pytest.mark.parametrize("entity_type", EntityTypeParams)
@pytest.mark.parametrize("data_format", ['parquet', 'json'])
@pytest.mark.parametrize("accept_content", [
    'application/x-parquet',
    'application/json',
])
def test_add_curve_by_chunk_different_cols(dasked_test_app_without_consistency_client, entity_type, data_format,
                                           accept_content):
    """ Create session, append chunking with consecutive index, validate session """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type,
                   record_id=record_id,
                   data_format=data_format,
                   cols_ranges=[(['MD', 'X'], range(5, 20)),
                                (['Y'], range(5, 20)),
                                (['Z'], range(5, 20))])

    data_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': accept_content})
    assert data_response.status_code == 200
    with_new_col = _create_df_from_response(data_response)
    # with_new_col = pd.DataFrame.from_dict(data_response.json())
    assert list(with_new_col.columns) == ['MD', 'X', 'Y', 'Z']
    assert with_new_col.shape == (15, 4)


@pytest.mark.parametrize("entity_type", EntityTypeParams)
@pytest.mark.parametrize("data_format", ['parquet', 'json'])
@pytest.mark.parametrize("accept_content", [
    'application/x-parquet',
    'application/json',
])
def test_add_curve_by_chunk_same_cols(dasked_test_app_without_consistency_client, entity_type, data_format,
                                      accept_content):
    """ Create session, append chunking with consecutive index, validate session """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type, record_id=record_id, data_format=data_format,
                   cols_ranges=[(['X'], range(10)),
                                (['X'], range(10, 20)),
                                (['X'], range(20, 30))])

    data_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': accept_content})
    assert data_response.status_code == 200
    with_new_col = _create_df_from_response(data_response)
    if accept_content == 'application/json':
        with_new_col.sort_index(inplace=True)  # TODO need to be investigate. Why the index is mixed up

    assert list(with_new_col.columns) == ['X']
    assert with_new_col.shape == (30, 1)
    assert with_new_col.index[0] == 0
    assert with_new_col.index[-1] == 29


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_add_curve_by_chunk_same_cols_overlapped_index(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with consecutive index, validate session """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    chunk_dfs = _create_chunks(client, entity_type, record_id=record_id,
                               cols_ranges=[(['MD', 'X'], range(20)),
                                            (['MD', 'X'], range(10, 30)),
                                            (['MD', 'X'], range(25, 40))])

    get_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': 'application/x-parquet'})
    assert get_response.status_code == 200
    result_df = _create_df_from_response(get_response)

    chunk_1, chunk_2, chunk_3 = chunk_dfs
    assert result_df.loc[0:9].compare(chunk_1.loc[0:9]).empty
    assert result_df.loc[10:24].compare(chunk_2.loc[10:24]).empty
    assert result_df.loc[25:40].compare(chunk_3.loc[25:40]).empty


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_add_curve_by_chunk_overlap_different_cols(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with consecutive index, validate session """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type, record_id=record_id, cols_ranges=[(['MD', 'A'], range(5, 10)),
                                                                          (['B'], range(8)),  # overlap left side
                                                                          (['C'], range(8, 15)),  # overlap left side
                                                                          (['D'], range(6, 8)),  # within
                                                                          (['E'], range(15)),  # overlap both side
                                                                          ])

    data_response = client.get(f'{chunking_url}/{record_id}/data?orient=columns',
                               headers={'Accept': 'application/json'})
    assert data_response.status_code == 200
    with_new_col = pd.DataFrame.from_dict(data_response.json())
    assert list(with_new_col.columns) == ['A', 'B', 'C', 'D', 'E', 'MD']
    assert with_new_col.shape == (15, 6)


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_abandon_session_with_data_push_data_again(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with consecutive index, abort sessions """
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    chunk_1 = generate_df(['MD', 'X'], range(5, 10))
    client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                data=chunk_1.to_json(orient='split'),
                headers={'Content-Type': 'application/json'})

    abort_session_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}',
                                          json={'state': 'abandon'})
    assert abort_session_response.status_code == 200
    assert abort_session_response.json()['state'] == SessionState.Abandoned
    assert abort_session_response.json()['version'] == None

    chunk_2 = generate_df(['MD', 'X'], range(11, 20))
    chunk2_response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                  data=chunk_2.to_json(orient='split'),
                                  headers={'Content-Type': 'application/json'})
    assert chunk2_response.status_code == 400


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_abandon_no_data_session(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    commit_unknown_session_response = client.patch(f'{chunking_url}/{record_id}/sessions/123456',
                                                   json={'state': 'commit'})
    assert commit_unknown_session_response.status_code == 404

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'abandon'})
    assert commit_response.status_code == 200


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_session_commit_no_data(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert commit_response.status_code == 422  # todo: expected behavior ?


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_session_double_abandon(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    abort_session_response_try1 = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}',
                                               json={'state': 'abandon'})
    assert abort_session_response_try1.status_code == 200

    abort_session_response_try2 = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}',
                                               json={'state': 'abandon'})
    assert abort_session_response_try2.status_code == 409


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_valid_session_double_commit(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    chunk_1 = generate_df(['MD', 'X'], range(5, 10))
    client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                data=chunk_1.to_json(orient='split'),
                headers={'Content-Type': 'application/json'})

    abort_session_response_try1 = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}',
                                               json={'state': 'commit'})
    assert abort_session_response_try1.status_code == 200

    abort_session_response_try2 = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}',
                                               json={'state': 'commit'})
    assert abort_session_response_try2.status_code == 409


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_session_unknown_record(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = dasked_test_app_without_consistency_client
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/123456/sessions', json={'mode': 'update'})

    assert session_response.status_code == 404


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_creates_two_sessions_one_record_with_chunks_different_format(dasked_test_app_without_consistency_client,
                                                                      entity_type):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type, record_id=record_id, data_format='json', cols_ranges=[(['X'], range(5, 20))])
    _create_chunks(client, entity_type, record_id=record_id, data_format='parquet', cols_ranges=[(['Y'], range(5, 20)),
                                                                                                 (['Z'], range(5, 20))])
    data_response = client.get(f'{chunking_url}/{record_id}/data')
    assert data_response.status_code == 200
    df = _create_df_from_response(data_response)
    assert df.shape == (15, 3)


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_creates_two_sessions_two_record_with_chunks(dasked_test_app_without_consistency_client, entity_type):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    another_record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type, record_id=record_id, cols_ranges=[(['X'], range(5, 20))])
    _create_chunks(client, entity_type, record_id=another_record_id, cols_ranges=[(['Y'], range(0, 10)),
                                                                                  (['Z'], range(5, 10))])
    data_response = client.get(f'{chunking_url}/{record_id}/data')
    assert data_response.status_code == 200
    df = _create_df_from_response(data_response)
    assert list(df.columns) == ['X']
    assert df.shape == (15, 1)

    another_data_response = client.get(f'{chunking_url}/{another_record_id}/data')
    assert another_data_response.status_code == 200
    other_df = _create_df_from_response(another_data_response)
    assert list(other_df.columns) == ['Y', 'Z']
    assert other_df.shape == (10, 2)


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_session_sent_same_col_different_types(dasked_test_app_without_consistency_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    chunk_1 = generate_df(['MD', 'X'], range(10))
    chunk_response_1 = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                   data=chunk_1.to_json(orient='split'),
                                   headers={'Content-Type': 'application/json'})
    assert chunk_response_1.status_code == 200

    chunk_2 = generate_df(['float_MD', 'str_X'], range(10, 20))
    chunk_2.rename(columns={'float_MD': 'MD', 'str_X': 'X'}, inplace=True)
    chunk_response_2 = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                   data=chunk_2.to_json(orient='split'),
                                   headers={'Content-Type': 'application/json'})
    assert chunk_response_2.status_code == 200

    commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert commit_response.status_code == 422


def _df_to_pyarrow_parquet(df_data: pd.DataFrame):
    """ Return a buffer containing parquet format file from the given dataframe """

    table = pa.Table.from_pandas(df=df_data)
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    return buf.getvalue().to_pybytes()


@pytest.mark.parametrize("entity_type", EntityTypeParams)
@pytest.mark.parametrize("columns_type", [
    [int(42), float(-42)],
    [int(42), float(-42), str('forty two')]
])
@pytest.mark.parametrize("content_type_header,create_func", [
    ('application/x-parquet', lambda df: _df_to_pyarrow_parquet(df)),
    ('application/json', lambda df: df.to_json(orient='split', date_format='iso')),
])
def test_session_chunk_int(dasked_test_app_without_consistency_client, entity_type, content_type_header, create_func,
                           columns_type):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    json_data = {t: np.random.rand(10) for t in columns_type}
    df_data = pd.DataFrame(json_data)
    data_to_send = create_func(df_data)

    headers = {'content-type': content_type_header}
    expected_code = 422

    # there is a side effect with parquet format, if at least one col is str, then all cols are casted into str
    if content_type_header.endswith('parquet') and any((type(c) is str for c in columns_type)):
        expected_code = 200

    # for legacy Log entity, column type as int are automatically casted to string to ensure backward compatibility
    if content_type_header.endswith('json') and entity_type == 'Log':
        expected_code = 200

    write_response = client.post(f'{chunking_url}/{record_id}/data', data=data_to_send, headers=headers)
    assert write_response.status_code == expected_code

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    chunk_response_1 = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                   data=data_to_send,
                                   headers=headers)
    assert chunk_response_1.status_code == expected_code


@pytest.mark.parametrize("columns", [[int(42), float(-42)], []])
def test_legacy_logs_int_columns(dasked_test_app_without_consistency_client, columns):
    """
        Ensure legacy v2 Log containing columns name as int type are correctly converted to string
        to ensure to_parquet is possible.
    """
    client = dasked_test_app_without_consistency_client
    entity_type = "Log"

    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']
    base_url = Definitions[entity_type]['base_url']

    json_data = {t: np.random.rand(10) for t in columns}
    df_data = pd.DataFrame(json_data)
    data_to_send = df_data.to_json(orient='split', date_format='iso')

    write_legacy_log_response = client.post(f'{base_url}/{record_id}/data',
                                            data=data_to_send,
                                            headers={'content-type': 'application/json'})
    assert write_legacy_log_response.status_code == 200

    read_dask_log_response = client.get(f'{chunking_url}/{record_id}/data',
                                        headers={'content-type': 'application/parquet'})
    assert read_dask_log_response.status_code == 200
    result_df = _create_df_from_response(read_dask_log_response)
    assert ptypes.is_string_dtype(result_df.columns)


@pytest.mark.parametrize("data_format", ['parquet', 'json'])
@pytest.mark.parametrize("accept_content", ['application/x-parquet', 'application/json'])
@pytest.mark.parametrize("columns_name", [
    list(map(str, range(100))),
    list(map(lambda x: f'test_{x}', range(100))),
    list(map(lambda x: f'{x}_test_{x % 10}', range(100)))
])
def test_nat_sort_columns(dasked_test_app_without_consistency_client, data_format, accept_content, columns_name):
    """ Create session, append chunking with consecutive index, validate session """

    entity_type = 'WellLog'
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type, record_id=record_id, data_format=data_format,
                   cols_ranges=[(columns_name, range(20))])

    data_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': accept_content})
    assert data_response.status_code == 200
    response_df = _create_df_from_response(data_response)
    assert list(response_df.columns) == columns_name


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
def test_session_update_previous_version(dasked_test_app_without_consistency_client, entity_type):
    """ create a session update on a previous version """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']
    base_url = Definitions[entity_type]['base_url']
    headers = {'Content-Type': 'application/x-parquet'}
    nb_rows = 5
    version_data = [
        generate_df(['MD', 'X', 'Y'], range(nb_rows)),
        generate_df(['MD', 'X', 'Z'], range(nb_rows)),
        generate_df(['MD', 'A', 'B'], range(nb_rows))
    ]

    # create the different version of data
    for data in version_data:
        write_response = client.post(f'{chunking_url}/{record_id}/data',
                                     data=data.to_parquet(engine="pyarrow"),
                                     headers=headers)
        assert write_response.status_code == 200

    versions_response = client.get(f'{base_url}/{record_id}/versions')
    assert versions_response.status_code == 200
    versions = versions_response.json()['versions']
    versions_with_data = zip(versions[1:], version_data)
    assert len(versions) == len(version_data) + 1

    # update specific versions
    for from_version, data in versions_with_data:
        session_response = client.post(f'{chunking_url}/{record_id}/sessions',
                                       json={"fromVersion": from_version, 'mode': 'update'})
        assert session_response.status_code == 200
        session_id = session_response.json()['id']

        new_curve = generate_df(['New'], range(nb_rows))
        chunk_response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                     data=new_curve.to_parquet(engine="pyarrow"),
                                     headers=headers)
        assert chunk_response.status_code == 200

        commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
        assert commit_response.status_code == 200

        # check result
        get_response = client.get(f'{chunking_url}/{record_id}/data')
        assert get_response.status_code == 200
        res_df = _create_df_from_response(get_response)
        expected_df = data
        expected_df['New'] = new_curve['New']
        expected_df = expected_df[sorted(expected_df.columns)]
        pd.testing.assert_frame_equal(expected_df, res_df)


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
def test_parquet_maintain_float_type(dasked_test_app_without_consistency_client, entity_type):
    """ send float32 and float64 columns and check if the type is maintain """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    df = generate_df(['MD', 'float_32', 'float_64'], range(5))
    df = df.astype({'float_32': 'float32', 'float_64': 'float64'})

    # Without session
    write_response = client.post(f'{chunking_url}/{record_id}/data',
                                 data=df.to_parquet(engine="pyarrow"),
                                 headers={'Content-Type': 'application/x-parquet'})
    assert write_response.status_code == 200
    get_response = client.get(f'{chunking_url}/{record_id}/data')
    assert get_response.status_code == 200
    res_df = _create_df_from_response(get_response)
    pd.testing.assert_frame_equal(df, res_df)

    # With session
    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    new_chunk = generate_df(['MD', 'float_32', 'float_64'], range(5, 10))
    new_chunk = new_chunk.astype({'float_32': 'float32', 'float_64': 'float64'})

    chunk_response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                 data=new_chunk.to_parquet(engine="pyarrow"),
                                 headers={'Content-Type': 'application/x-parquet'})
    assert chunk_response.status_code == 200
    commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert commit_response.status_code == 200

    df = pd.concat([df, new_chunk])

    get_response = client.get(f'{chunking_url}/{record_id}/data')
    assert get_response.status_code == 200
    res_df = _create_df_from_response(get_response)
    pd.testing.assert_frame_equal(df, res_df)

    # with curve selection
    for curve in ('float_32', 'float_64'):
        get_response = client.get(f'{chunking_url}/{record_id}/data', params={'curves': curve})
        assert get_response.status_code == 200
        res_df = _create_df_from_response(get_response)
        pd.testing.assert_frame_equal(df[[curve]], res_df)


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_send_json_parquet_in_one_session(dasked_test_app_without_consistency_client, entity_type):
    """ send data in json format first and then in parquet format in one session,
        check if the session can be committed successfully """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)

    # Create a session
    chunking_url = Definitions[entity_type]['chunking_url']
    create_session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'overwrite'})
    assert create_session_response.status_code == 200
    session_data = create_session_response.json()
    session_id = session_data['id']

    # append first chunk - JSON
    chunk_1 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(5, 10))
    response_chunk_1 = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                   json=chunk_1.to_dict(orient='split'))

    assert response_chunk_1.status_code == 200

    # append first chunk - PARQUET
    chunk_2 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(15, 20))
    headers = {'content-type': 'application/x-parquet'}
    response_chunk_2 = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                   data=chunk_2.to_parquet(engine="pyarrow"), headers=headers)
    assert response_chunk_2.status_code == 200

    # COMMIT session
    commit_session_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}',
                                           json={'state': 'commit'})

    assert commit_session_response.status_code == 200

    get_response = client.get(f'{chunking_url}/{record_id}/data')
    assert get_response.status_code == 200


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_send_parquet_json_in_one_session(dasked_test_app_without_consistency_client, entity_type):
    """ send data in parquet format first and then in json format in one session,
    check if the session can be committed successfully  """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)

    # Create a session
    chunking_url = Definitions[entity_type]['chunking_url']
    create_session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'overwrite'})
    assert create_session_response.status_code == 200
    session_data = create_session_response.json()
    session_id = session_data['id']

    # append first chunk - PARQUET
    chunk_1 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(15, 20))
    headers = {'content-type': 'application/x-parquet'}

    response_chunk_1 = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                   data=chunk_1.to_parquet(engine="pyarrow"), headers=headers)
    assert response_chunk_1.status_code == 200

    # append first chunk - JSON
    chunk_2 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(5, 10))
    response_chunk_2 = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                   json=chunk_2.to_dict(orient='split'))

    assert response_chunk_2.status_code == 200

    # COMMIT session
    commit_session_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}',
                                           json={'state': 'commit'})

    assert commit_session_response.status_code == 200

    get_response = client.get(f'{chunking_url}/{record_id}/data')
    assert get_response.status_code == 200


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_send_parquet_json_with_two_session(dasked_test_app_without_consistency_client, entity_type):
    """ send parquet and json separately with two session, check if each session can be committed successfully"""
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    # append chunk - JSON
    _create_chunks(client=client,
                   entity_type=entity_type,
                   cols_ranges=[
                       (['COLUMN_MD', 'COLUMN_X'], range(5, 10)),
                       (['COLUMN_MD', 'COLUMN_X'], range(15, 20))],
                   record_id=record_id,
                   session_mode='overwrite',
                   data_format='json')

    # append chunk - PARQUET
    _create_chunks(client=client,
                   entity_type=entity_type,
                   cols_ranges=[
                       (['COLUMN_MD', 'COLUMN_X'], range(5, 10))],
                   record_id=record_id,
                   session_mode='update',
                   data_format='parquet')


@pytest.fixture()
def dataframe_for_filters():
    dic = {
        "A": range(20),
        "B": np.arange(20.0),
        "C": [str(i) for i in range(20)],
        "D": [i % 2 == 0 for i in range(20)]
    }
    return pd.DataFrame(dic, index=range(20))


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("params, expected", [
    (['A:lt:5'], lambda df: df.loc[df['A'] < 5]),
    (['A:lte:5'], lambda df: df.loc[df['A'] <= 5]),
    (['A:eq:5'], lambda df: df.loc[df['A'] == 5]),
    (['A:neq:5'], lambda df: df.loc[df['A'] != 5]),
    (['A:gt:5'], lambda df: df.loc[df['A'] > 5]),
    (['A:gte:5'], lambda df: df.loc[df['A'] >= 5]),
    (['A:in:5,6,7'], lambda df: df.loc[df['A'].isin([5, 6, 7])]),
    (['B:lt:5.0'], lambda df: df.loc[df['B'] < 5.0]),
    (['B:lte:5.0'], lambda df: df.loc[df['B'] <= 5.0]),
    (['B:eq:5.0'], lambda df: df.loc[df['B'] == 5.0]),
    (['B:neq:5.0'], lambda df: df.loc[df['B'] != 5.0]),
    (['B:gt:5.0'], lambda df: df.loc[df['B'] > 5.0]),
    (['B:gte:5.0'], lambda df: df.loc[df['B'] >= 5.0]),
    (['B:in:5.0,6.0,7.0'], lambda df: df.loc[df['B'].isin([5.0, 6.0, 7.0])]),
    (['C:gt:5'], lambda df: df.loc[df['C'] > '5']),
    (['C:gte:5'], lambda df: df.loc[df['C'] >= '5']),
    (['C:gte:5s+++'], lambda df: df.loc[df['C'] >= '5s+++']),
    (['C:eq:sss'], lambda df: df.loc[df['C'] >= 'sss']),
    (['C:lt:5'], lambda df: df.loc[df['C'] < '5']),
    (['C:lte:5'], lambda df: df.loc[df['C'] <= '5']),
    (['C:eq:5'], lambda df: df.loc[df['C'] == '5']),
    (['C:neq:5'], lambda df: df.loc[df['C'] != '5']),
    (['C:in:5,6,7'], lambda df: df.loc[df['C'].isin(['5', '6', '7'])]),
    (['C:eq:abc:def'], lambda df: df.loc[df['C'] == 'abc:def']),
    (['D:eq:True'], lambda df: df.loc[df['D'] == True]),
    (['D:neq:True'], lambda df: df.loc[df['D'] != True]),
    (['D:eq:False'], lambda df: df.loc[df['D'] == False]),
    (['A:lt:5', 'B:gte:5.0', 'D:eq:True'], lambda df: df.loc[(df['A'] < 5) & (df['B'] >= 5.0) & (df['D'] == True)]),
    (['A:lt:5', 'B:lte:5.0', 'D:eq:True'], lambda df: df.loc[(df['A'] < 5) & (df['B'] <= 5.0) & (df['D'] == True)])
])
def test_get_bulk_data_with_filters(dasked_test_app_without_consistency_client, entity_type, params, expected,
                                    dataframe_for_filters):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                     data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}

    response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
                                   params={'filter': params})
    df = _create_df_from_response(response_get_data)
    assert_frame_equal(df, expected(dataframe_for_filters))


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("filter, limit, expected", [(['A:gt:5'], 5, lambda df: df.loc[df['A'] > 5]),
                                                     (['A:lt:5'], 5, lambda df: df.loc[df['A'] < 5]),
                                                     (['C:eq:5'], 5, lambda df: df.loc[df['A'] == 5]),
                                                     (['A:lt:5', 'B:lte:5.0', 'D:eq:True'], 5, lambda df: df.loc[
                                                         (df['A'] < 5) & (df['B'] <= 5.0) & (df['D'] == True)])])
def test_get_bulk_data_with_filters_curves_offset(dasked_test_app_without_consistency_client, entity_type, filter,
                                                  limit, expected, dataframe_for_filters):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                     data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}
    curve = ['A,B']
    for i in range(0, math.ceil(20 / limit)):
        response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
                                       params={'filter': filter, 'curves': curve, 'offset': i * limit, 'limit': limit})
        df = _create_df_from_response(response_get_data)
        df_expected = expected(dataframe_for_filters).iloc[i * limit:(i + 1) * limit][['A', 'B']]
        assert_frame_equal(df, df_expected)


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("filter, limit, curves, expected", [(['A:gt:5'], 5, ['A,B'], [5, 5, 4, 0]),
                                                             (['A:lt:5'], 5, ['A,C'], [5, 0, 0, 0]),
                                                             (['D:eq:True'], 5, ['C,D'], [5, 5, 0, 0]),
                                                             (['C:in:5,6,7'], 5, ['B,D'], [3, 0, 0, 0])
                                                             ])
def test_get_bulk_data_with_filters_curves_offset_describe(dasked_test_app_without_consistency_client, entity_type,
                                                           filter, limit, expected, dataframe_for_filters, curves):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                     data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}
    for i in range(0, math.ceil(20 / limit)):
        response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
                                       params={'filter': filter, 'curves': curves, 'offset': i * limit, 'limit': limit,
                                               'describe': True})
        assert response_get_data.json()['numberOfRows'] == expected[i]
        assert response_get_data.json()['columns'] == curves[0].split(',')


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("params, content, failure_status", [
    (['M:lt:5'], "filter error: The columns:['M'] to be filtered do not exist", 400),
    (['A:lt:5', 'A:lt:7'], 'filter error: Same operator on the same column', 400),
    (['A:xx:5'], '', 422),  # 422 since handled by regex at query param declaration,
    (['A:lt'], '', 422)
])
def test_get_bulk_data_with_filters_fail(dasked_test_app_without_consistency_client, entity_type, params, content,
                                         failure_status, dataframe_for_filters):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                     data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}

    response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
                                   params={'filter': params})

    if content:
        assert response_get_data.json()['detail'] == content
    assert response_get_data.status_code == failure_status


# todo - concurrent sessions using fromVersion in Integrations tests

@pytest.mark.parametrize("entity_type", EntityTypeParams)
@pytest.mark.parametrize("reserved_columns_name", ['__index_level_0__', '__null_dask_index__'])
@pytest.mark.parametrize("use_custom_index", [True, False])
def test_none_in_index_error(dasked_test_app_without_consistency_client, entity_type, reserved_columns_name,
                             use_custom_index):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    # A column named '__index_level_0__' is internally used by PyArrow to save the index.
    # Sending column named the same way as regular column causes problems to read them with Dask.
    df = generate_df(['float-COLUMN_MD', 'COLUMN_X', reserved_columns_name], range(50))

    if use_custom_index:
        df = df.set_index('float-COLUMN_MD')

    response_get_data = client.post(f'{chunking_url}/{record_id}/data',
                                    data=df.to_parquet(engine="pyarrow"),
                                    headers={'content-type': 'application/parquet'})
    assert response_get_data.status_code == 422


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_read_too_many_columns(dasked_test_app_without_consistency_client, entity_type, local_bulk_persistence_config):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    max_cols_count = local_bulk_persistence_config.max_columns_return

    response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert response.status_code == 200
    session_id = response.json()['id']

    df = generate_df([f'var[{i}]' for i in range(int(max_cols_count/2) + 1)], range(5))
    response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                           data=df.to_parquet(engine="pyarrow"),
                           headers={'content-type': 'application/parquet'})
    assert response.status_code == 200
    df = generate_df([f'var2[{i}]' for i in range(int(max_cols_count/2) + 1)], range(5))
    response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                           data=df.to_parquet(engine="pyarrow"),
                           headers={'content-type': 'application/parquet'})
    assert response.status_code == 200

    response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert response.status_code == 200

    get_describe_response = client.get(f'{chunking_url}/{record_id}/data',
                                       headers={'Accept': 'application/parquet'},
                                       params={'describe': True})
    assert get_describe_response.status_code == 200

    get_all_cols_response = client.get(f'{chunking_url}/{record_id}/data',
                                       headers={'Accept': 'application/parquet'})
    assert get_all_cols_response.status_code == 400
    assert "Too many columns: requested" in get_all_cols_response.json().get('detail', str())

    get_response = client.get(f'{chunking_url}/{record_id}/data',
                              headers={'Accept': 'application/parquet'},
                              params={'curves': f'var[0:{max_cols_count - 1}]'})
    assert get_response.status_code == 200

    get_response = client.get(f'{chunking_url}/{record_id}/data',
                              headers={'Accept': 'application/parquet'},
                              params={'curves': f'var[0:{int(max_cols_count/2) + 1}],var2[0:{int(max_cols_count/2) + 1}]'})
    assert get_response.status_code == 400
    assert "Too many columns: requested" in get_response.json().get('detail', str())


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_many_columns_ensure_effective_cols_count_matter(dasked_test_app_without_consistency_client, entity_type, local_bulk_persistence_config):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    max_cols_count = 100
    local_bulk_persistence_config.max_columns_return = max_cols_count

    effective_cols_count = 50
    df = generate_df([f'var[{i}]' for i in range(effective_cols_count)], range(2))
    write_response = client.post(f'{chunking_url}/{record_id}/data',
                                 data=df.to_parquet(engine="pyarrow"),
                                 headers={'content-type': 'application/parquet'})
    assert write_response.status_code == 200

    get_response = client.get(f'{chunking_url}/{record_id}/data',
                              headers={'Accept': 'application/parquet'},
                              params={'curves': f'var[0:{max_cols_count * 2}]'})
    assert get_response.status_code == 200, \
        "Ensure only existing columns are taken into account for max cols limit"


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_write_too_many_columns(dasked_test_app_without_consistency_client, entity_type, local_bulk_persistence_config):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    df = generate_df([f'var[{i}]' for i in range(local_bulk_persistence_config.max_columns_per_chunk_write + 1)], range(2))
    response = client.post(f'{chunking_url}/{record_id}/data',
                           data=df.to_parquet(engine="pyarrow"),
                           headers={'content-type': 'application/parquet'})
    assert response.status_code == 422
    assert 'Too many columns' in response.text


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_write_too_many_columns_session(dasked_test_app_without_consistency_client, entity_type, local_bulk_persistence_config):
    """ send parquet and json separately with two session, check if each session can be committed successfully"""
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)

    chunking_url = Definitions[entity_type]["chunking_url"]
    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'overwrite'})
    session_id = session_response.json()['id']

    df = generate_df([f'var[{i}]' for i in range(local_bulk_persistence_config.max_columns_per_chunk_write + 1)], range(2))
    response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                           data=df.to_parquet(engine="pyarrow"),
                           headers={'content-type': 'application/parquet'})
    assert response.status_code == 422
    assert 'Too many columns' in response.text


def test_session_update_previous_storage_version(dasked_test_app_without_consistency_client):
    """ create a session update on a previous version, so only for V2 """

    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, 'Log')
    chunking_url = Definitions['Log']['chunking_url']
    base_url = Definitions['Log']['base_url']

    df_previous = pd.DataFrame({'MD': [0.5, 1.5], 'X': [10, 11]}, index=[0, 1])
    df_update = pd.DataFrame({'MD': [2.5, 3.5], 'X': [20, 21]}, index=[2, 3])

    headers = {'Content-Type': 'application/x-parquet'}

    # post bulk with legacy storage version
    write_response = client.post(f'{base_url}/{record_id}/data',
                                 data=df_previous.to_json(orient='split'))
    assert write_response.status_code == 200

    # update using new (alpha) storage V2
    response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert response.status_code == 200
    session_id = response.json()['id']

    response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                           data=df_update.to_parquet(engine="pyarrow"),
                           headers=headers)
    assert response.status_code == 200

    response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert response.status_code == 200

    # check result
    get_response = client.get(f'{chunking_url}/{record_id}/data',
                              headers={'Accept': 'application/parquet'})
    df: pd.DataFrame = _create_df_from_response(get_response)
    assert list(df['X'].values) == [10, 11, 20, 21]


from unittest import mock
from app.bulk_persistence.dask.traces import TracingMode
from app.bulk_persistence import SessionsStorage, SessionState, SessionUpdateMode


def assert_mock_chunk(tracing_mock, chunk_df):
    tracing_mock.assert_called_with({"df rows count": chunk_df.shape[0], "df columns count": chunk_df.shape[1],
                                     'df index start': str(chunk_df.index[0]), 'df index end': str(chunk_df.index[-1]),
                                     'df index type': str(chunk_df.index.dtype)
                                     }, TracingMode.CURRENT_SPAN)


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_bulk_tracing(dasked_test_app_without_consistency_client, entity_type):
    client = dasked_test_app_without_consistency_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    with mock.patch('app.bulk_persistence.dask.traces._add_trace_attributes',
                    return_value=mock.MagicMock()) as mock_mock:
        session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
        assert session_response.status_code == 200
        session_id = session_response.json()['id']
        send_chunk_url = f'{chunking_url}/{record_id}/sessions/{session_id}/data'

        chunk_1 = generate_df(['MD', 'X'], range(0, 5))
        _send_chunk(client, send_chunk_url, chunk_1, 'parquet')
        assert_mock_chunk(mock_mock, chunk_1)

        chunk_2 = generate_df(['MD', 'X'], range(10, 30))
        _send_chunk(client, send_chunk_url, chunk_2, 'parquet')
        assert_mock_chunk(mock_mock, chunk_2)

        chunk_3 = generate_df(['Y', 'Z'], range(10, 30))
        _send_chunk(client, send_chunk_url, chunk_3, 'parquet')
        assert_mock_chunk(mock_mock, chunk_3)

        commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
        assert commit_response.status_code == 200

        mock_mock.assert_any_call({'session-mode': SessionUpdateMode.Update}, TracingMode.ROOT_SPAN)
        mock_mock.assert_any_call({'chunks-count': 3}, TracingMode.ROOT_SPAN)
        mock_mock.assert_any_call({'chunks-distinct-index': 2}, TracingMode.ROOT_SPAN)
        mock_mock.assert_any_call({'catalog-row-count': 25, 'catalog-col-count': 4}, TracingMode.ROOT_SPAN)

        data_response = client.get(f'{chunking_url}/{record_id}/data', headers={'content-type': 'application/parquet'})
        assert data_response.status_code == 200
        retrieved_df = _create_df_from_response(data_response)
        assert_mock_chunk(mock_mock, retrieved_df)

        data_df = generate_df(['A', 'B', 'C'], range(0, 30))
        write_response = client.post(f'{chunking_url}/{record_id}/data', data=_df_to_format(data_df, 'parquet'),
                                     headers={'content-type': 'application/parquet'})
        assert write_response.status_code == 200
        assert_mock_chunk(mock_mock, data_df)

# todo:
#  - concurrent sessions using fromVersion in Integrations tests
#  - index: check if dataframe has an index
#  - test timeout ?
#  - how to choose the index?
