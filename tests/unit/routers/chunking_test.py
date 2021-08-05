import asyncio
import io
from tempfile import TemporaryDirectory

from fastapi import Header
from fastapi.testclient import TestClient
import pytest
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa

from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from osdu.core.api.storage.blob_storage_base import BlobStorageBase

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage, make_local_dask_bulk_storage

from app.clients import StorageRecordServiceClient
from app.persistence.sessions_storage import SessionsStorage, SessionState
from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.auth.auth import require_opendes_authorized_user
from app.middleware import require_data_partition_id
from app.helper import traces
from app.utils import Context, DaskClient
from app import conf

from tests.unit.persistence.dask_blob_storage_test import generate_df
from tests.unit.test_utils import nope_logger_fixture


Definitions = {
    'WellLog': {
        'api_version': 'v3',
        'base_url': '/ddms/v3/welllogs',
        'chunking_url': '/alpha/ddms/v3/welllogs',  # TODO: update when no longer alpha
        'kind': 'osdu:wks:work-product-component--WellLog:1.1.0',
        'record_data': {
            "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "Curves": [{"CurveID": "MD"}, {"CurveID": "X"}]
        }
    },

    'WellboreTrajectory': {
        'api_version': 'v3',
        'base_url': '/ddms/v3/wellboretrajectories',
        'chunking_url': '/alpha/ddms/v3/wellboretrajectories',  # TODO: update when no longer alpha
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
        'chunking_url': '/alpha/ddms/v2/logs',  # TODO: update when no longer alpha
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
    elif content_type == 'text/csv; charset=utf-8':
        return pd.read_csv(f, index_col=0)
    elif content_type == 'application/json':
        return pd.read_json(f, dtype=True, orient='split', convert_axes=False)
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
    for name, col in result_df.items():
        if name.startswith('date'):
            result_df[name] = result_df[name].astype('datetime64[ns]')

    return result_df


@pytest.fixture
def init_fixtures(nope_logger_fixture, monkeypatch):
    with TemporaryDirectory() as tmp_dir:
        monkeypatch.setenv(name='USE_LOCALFS_BLOB_STORAGE_WITH_PATH', value=tmp_dir)
        conf.Config = conf.ConfigurationContainer.with_load_all()
        yield


@pytest.fixture(scope="module")
def event_loop():  # all tests will share the same loop
    loop = asyncio.get_event_loop()
    yield loop
    # teardown
    loop.run_until_complete(DaskClient.close())
    loop.close()
    

@pytest.fixture
def dasked_test_app(init_fixtures):
    from app.wdms_app import wdms_app, enable_alpha_feature
    from app.wdms_app import app_injector

    enable_alpha_feature()

    with TemporaryDirectory() as tmp_dir:
        local_blob_storage = LocalFSBlobStorage(directory=tmp_dir)

        async def storage_service_builder(*args, **kwargs):
            return StorageRecordServiceBlobStorage(local_blob_storage, 'myProject', 'myContainer')

        async def set_default_partition(data_partition_id: str = Header('opendes')):
            Context.set_current_with_value(partition_id=data_partition_id)

        async def blob_storage_builder(*args, **kwargs):
            return local_blob_storage

        async def sessions_storage_builder(*args, **kwargs):
            return SessionsStorage(local_blob_storage)

        async def dask_blob_storage_builder() -> DaskBulkStorage:
            return await make_local_dask_bulk_storage(base_directory=tmp_dir)

        app_injector.register(DaskBulkStorage, dask_blob_storage_builder)
        app_injector.register(BlobStorageBase, blob_storage_builder)
        app_injector.register(SessionsStorage, sessions_storage_builder)
        app_injector.register(StorageRecordServiceClient, storage_service_builder)

        async def do_nothing():
            # empty method
            pass

        wdms_app.dependency_overrides[require_opendes_authorized_user] = do_nothing
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        # Initialize traces exporter in app, like it is in app's startup decorator
        wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

        yield wdms_app

        wdms_app.dependency_overrides = {}  # clean up


@pytest.fixture
def setup_client(dasked_test_app):
    yield TestClient(dasked_test_app)


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
def test_send_all_data_once(setup_client,
                            entity_type,
                            columns,
                            content_type_header,
                            create_func,
                            accept_content):
    client = setup_client
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

    if content_type_header.endswith('parquet') and accept_content.endswith('json'):
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
def test_send_all_data_once_post_data_v2_get_data_v3(setup_client,
                                                     entity_type,
                                                     columns,
                                                     content_type_header,
                                                     create_func,
                                                     accept_content):
    client = setup_client
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
    # 'text/csv; charset=utf-8',
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
def test_overwrite_data_by_chunk_append(setup_client, entity_type, columns, content_type_header, create_func,
                                        accept_content, session_mode):
    """ Create session, append chunking with consecutive index, validate session """

    client = setup_client
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

        if data_format == 'json':
            headers = {'Content-Type': 'application/json'}
        elif data_format == 'parquet':
            headers = {'content-type': 'application/x-parquet'}
        else:
            raise ValueError(f"Unknown content-type: '{data_format}'")

        chunk_response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                     data=_df_to_format(chunk_df, data_format),
                                     headers=headers)
        assert chunk_response.status_code == 200  # todo: should it be 204?

    commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert commit_response.status_code == 200
    assert commit_response.json()['state'] == SessionState.Committed
    return created_dfs


@pytest.mark.parametrize("entity_type", EntityTypeParams)
@pytest.mark.parametrize("data_format", ['parquet', 'json'])
@pytest.mark.parametrize("accept_content", [
    'application/x-parquet',
    'text/csv; charset=utf-8',
    'application/json',
])
def test_add_curve_by_chunk_different_cols(setup_client, entity_type, data_format, accept_content):
    """ Create session, append chunking with consecutive index, validate session """

    client = setup_client
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
    'text/csv; charset=utf-8',
    'application/json',
])
def test_add_curve_by_chunk_same_cols(setup_client, entity_type, data_format, accept_content):
    """ Create session, append chunking with consecutive index, validate session """

    client = setup_client
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
def test_add_curve_by_chunk_same_cols_overlapped_index(setup_client, entity_type):
    """ Create session, append chunking with consecutive index, validate session """

    client = setup_client
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
def test_add_curve_by_chunk_overlap_different_cols(setup_client, entity_type):
    """ Create session, append chunking with consecutive index, validate session """

    client = setup_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type, record_id=record_id, cols_ranges=[(['MD', 'A'], range(5, 10)),
                                                                          (['B'], range(8)),  # overlap left side
                                                                          (['C'], range(8, 15)),  # overlap left side
                                                                          (['D'], range(6, 8)),  # within
                                                                          (['E'], range(15)),  # overlap both side
                                                                          ])

    data_response = client.get(f'{chunking_url}/{record_id}/data?orient=columns', headers={'Accept': 'application/json'})
    assert data_response.status_code == 200
    with_new_col = pd.DataFrame.from_dict(data_response.json())
    assert list(with_new_col.columns) == ['A', 'B', 'C', 'D', 'E', 'MD']
    assert with_new_col.shape == (15, 6)


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_abandon_session_with_data_push_data_again(setup_client, entity_type):
    """ Create session, append chunking with consecutive index, abort sessions """
    client = setup_client
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

    chunk_2 = generate_df(['MD', 'X'], range(11, 20))
    chunk2_response = client.post(f'{chunking_url}/{record_id}/sessions/{session_id}/data',
                                  data=chunk_2.to_json(orient='split'),
                                  headers={'Content-Type': 'application/json'})
    assert chunk2_response.status_code == 400


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_abandon_no_data_session(setup_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = setup_client
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
def test_session_commit_no_data(setup_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = setup_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/{record_id}/sessions', json={'mode': 'update'})
    assert session_response.status_code == 200
    session_id = session_response.json()['id']

    commit_response = client.patch(f'{chunking_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
    assert commit_response.status_code == 422  # todo: expected behavior ?


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_session_double_abandon(setup_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = setup_client
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
def test_valid_session_double_commit(setup_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = setup_client
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
def test_session_unknown_record(setup_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = setup_client
    chunking_url = Definitions[entity_type]['chunking_url']

    session_response = client.post(f'{chunking_url}/123456/sessions', json={'mode': 'update'})
    assert session_response.status_code == 404


@pytest.mark.parametrize("entity_type", EntityTypeParams)
def test_creates_two_sessions_one_record_with_chunks_different_format(setup_client, entity_type):
    client = setup_client
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
def test_creates_two_sessions_two_record_with_chunks(setup_client, entity_type):
    client = setup_client
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
def test_session_sent_same_col_different_types(setup_client, entity_type):
    """ Create session, append chunking with overlapped index, validate session """
    client = setup_client
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
def test_session_chunk_int(setup_client, entity_type, content_type_header, create_func, columns_type):
    client = setup_client
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


@pytest.mark.parametrize("data_format", ['parquet', 'json'])
@pytest.mark.parametrize("accept_content", ['application/x-parquet', 'application/json'])
@pytest.mark.parametrize("columns_name", [
    list(map(str, range(100))),
    list(map(lambda x: f'test_{x}', range(100))),
    list(map(lambda x: f'{x}_test_{x%10}', range(100)))
])
def test_nat_sort_columns(setup_client, data_format, accept_content, columns_name):
    """ Create session, append chunking with consecutive index, validate session """

    entity_type = 'WellLog'
    client = setup_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']

    _create_chunks(client, entity_type, record_id=record_id, data_format=data_format,
                cols_ranges=[(columns_name, range(20))])

    data_response = client.get(f'{chunking_url}/{record_id}/data', headers={'accept': accept_content})
    assert data_response.status_code == 200
    response_df = _create_df_from_response(data_response)
    assert list(response_df.columns) == columns_name

@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
def test_session_update_previous_version(setup_client, entity_type):
    """ create a session update on a previous version """

    client = setup_client
    record_id = _create_record(client, entity_type)
    chunking_url = Definitions[entity_type]['chunking_url']
    base_url = Definitions[entity_type]['base_url']
    headers = headers={'Content-Type': 'application/x-parquet'}
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


# todo:
#  - concurrent sessions using fromVersion in Integrations tests
#  - index: check if dataframe has an index
#  - test timeout ?
#  - how to choose the index?
