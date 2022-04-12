import asyncio
import datetime
from typing import List

import mock
import numpy as np
import pytest

from app.bulk_persistence.statistics.exceptions import StatisticsNotFoundError, RequestedCurvesError
from tests.unit.test_utils import ctx_fixture
from tests.unit.generate_data import generate_df

from app.persistence.sessions_storage import Session, SessionUpdateMode, SessionState

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.statistics.bulk_statistics import BulkStatistics, grouper
from app.bulk_persistence.dask.dask_bulk_storage_local import make_local_dask_bulk_storage
from app.bulk_persistence import MimeTypes
from app.bulk_persistence.dataframe_validators import no_validation


@pytest.mark.parametrize("container", [
    list(range(10)),
    list()
])
@pytest.mark.parametrize("step", [
    0, 5, 10, 11
])
def test_grouper(container, step):
    result = list(grouper(step, container))
    for r in result:
        assert len(r) == min(step, len(container))


@pytest.fixture(scope="module")
def app_initialized_with_testclient(dask_client):
    """
    Fixture providing wdms_app started, along with a test client
    """
    # retrieve the dask_client starter, but let the app close it.
    # CAREFUL about the fixture scope
    with dask_client(autoclose_asynccontext=False) as dask_client_starter:
        # Mocking dask_client for app to use it
        with mock.patch('app.bulk_persistence.dask.client.DaskClient.create', dask_client_starter):
            yield dask_client_starter


@pytest.fixture()
async def bulk_stats_fixture(app_initialized_with_testclient, tmp_path, nope_logger_fixture, ctx_fixture) \
        -> (BulkStatistics, DaskBulkStorage):
    local_dask = await make_local_dask_bulk_storage(str(tmp_path))

    bulk_stats = BulkStatistics(dask_blob_storage=local_dask)
    bulk_stats.max_number_values = 500_000
    bulk_stats.max_colums_count = 100
    yield bulk_stats, local_dask

    local_dask.client.close()


async def add_bulk_data_to_fixture(dask_blob_storage, typed_df):
    session = create_test_bulk_session()

    parquet_data = typed_df.to_parquet(engine='pyarrow')

    await dask_blob_storage.add_chunk_in_session(parquet_data, MimeTypes.PARQUET, no_validation, session.recordId,
                                                 session.id)
    new_bulk_id = await dask_blob_storage.session_commit(session)
    assert new_bulk_id

    return session.recordId, new_bulk_id


async def add_bulk_data_by_chunks_to_fixture(dask_blob_storage, cols_with_index: List[tuple]):

    session = create_test_bulk_session()
    coroutines = []
    for columns_name, values_index in cols_with_index:
        chunk_df = generate_df(columns_name, values_index)

        cols_with_nan = [c for c in chunk_df.columns if c.endswith('nan')]
        for col_with_nan in cols_with_nan:
            col_data = chunk_df[col_with_nan]
            for i in range(0, col_data.size, 2):
                col_data[i] = np.NAN

        chunk_data = chunk_df.to_parquet(engine='pyarrow')

        routine = dask_blob_storage.add_chunk_in_session(chunk_data,
                                                         MimeTypes.PARQUET,
                                                         no_validation,
                                                         session.recordId,
                                                         session.id)
        coroutines.append(routine)

    for r in grouper(100, coroutines):
        await asyncio.gather(*r)

    new_bulk_id = await dask_blob_storage.session_commit(session)
    assert new_bulk_id
    return session.recordId, new_bulk_id


def create_test_bulk_session() -> Session:
    record_id = "my-record-id"
    session_id = "my-session-id"

    session = Session(id=session_id,
                      recordId=record_id,
                      fromVersion='123456',
                      mode=SessionUpdateMode.Overwrite,
                      expiry=datetime.datetime.now(),
                      createdTime=datetime.datetime.now(),
                      updatedTime=datetime.datetime.now(),
                      state=SessionState.Open
                      )
    return session


def _bulk_stats_columns() -> List[str]:
    """
        Return the expected list of columns of bulk stats
    """
    return sorted(['count', 'mean', 'min', '10%', '50%', '90%', 'max', 'std', 'total_count'])


def _bulk_stats_columns_if_date_type_only() -> List[str]:
    """
        # If there is only date, 'std' (standard deviation) is NaN then ignored from result
    """
    columns = _bulk_stats_columns()
    columns.remove('std')
    return columns


@pytest.mark.asyncio
@pytest.mark.parametrize("cols_name_by_index, expected_rows, expected_cols", [
    (
            [(['int-A', 'float-B', 'date-C', 'bool-D', 'string-E'], range(500))], 3, _bulk_stats_columns()
    ),
    (
            [(['date-C', 'date-D'], range(100))], 2, _bulk_stats_columns()
    ),
    (
            [(['int-A', 'float-B', 'date-C'], range(1_000_000))], 3, _bulk_stats_columns()
    ),
    (
            [
                (['float-A', 'float-B', 'float-C'], range(100_000)),
                (['float-A', 'float-B', 'float-C'], range(100_000, 200_000)),
                (['float-A', 'float-B', 'float-C'], range(400_000, 500_000)),
                (['float-A', 'float-B', 'float-C'], range(500_000, 1_000_000)),
            ],
            3, _bulk_stats_columns()
    ),
    (
            [
                (['float-A'], range(1_000_000)),
                (['float-B'], range(1_000_000)),
                (['float-A'], range(1_000_000, 2_000_000)),
                (['float-B'], range(1_000_000, 2_000_000)),
                (['float-A'], range(3_000_000, 4_000_000)),
                (['float-B'], range(3_000_000, 4_000_000)),
            ],
            2, _bulk_stats_columns()
    ),
    # todo: add test case with NaN values
])
async def test_bulk_statistics_get_bulk_statistics(bulk_stats_fixture, cols_name_by_index,
                                                   expected_rows, expected_cols):

    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)

    with pytest.raises(StatisticsNotFoundError):
        await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=None)

    futures = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri)
    await asyncio.gather(*futures)

    df_stats = await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=None)
    assert len(df_stats) == expected_rows
    assert sorted(list(df_stats.columns)) == expected_cols


@pytest.mark.asyncio
@pytest.mark.parametrize("cols_name_by_index, expected_shape", [
    (
            [(['int-A', 'float-B', 'date-C', 'bool-D', 'string-E'], range(500))],
            (3, len(_bulk_stats_columns_if_date_type_only()))
    ),
    (
            [(['int-A-nan', 'float-B', 'date-C-nan', 'bool-D', 'string-E'], range(500))],
            (3, len(_bulk_stats_columns_if_date_type_only()))
    ),
])
async def test_bulk_statistics_get_statistics(bulk_stats_fixture, cols_name_by_index, expected_shape):
    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)

    all_cols = []
    for requested_cols, _ in cols_name_by_index:
        all_cols.extend(requested_cols)
    distinct_cols = set(all_cols)
    valid_cols = [c for c in distinct_cols
                  if not c.startswith('bool') and not c.startswith('string')]

    assert valid_cols, "At least one columns needs to be valid for test cases below"

    futures = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri)
    await asyncio.gather(*futures)

    with pytest.raises(RequestedCurvesError):
        await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=['incorrect-column-name'])

    computable_col_plus_invalid_cols = [valid_cols[0], 'incorrect-column-name']
    with pytest.raises(RequestedCurvesError):
        await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=computable_col_plus_invalid_cols)

    not_computable_cols = ['bool-D', 'string-E']
    result_df_1 = await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=not_computable_cols)
    assert result_df_1.empty

    not_computable_cols_plus_valid_cols = not_computable_cols + [valid_cols[0]]
    result_df_2 = await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=not_computable_cols_plus_valid_cols)
    assert result_df_2.shape == (1, 9)
    assert result_df_2.index == [valid_cols[0]]

    result_df_with_nan_cols = await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=None)
    assert result_df_with_nan_cols.shape == (3, 9)
    assert list(result_df_with_nan_cols.index) == valid_cols


@pytest.mark.asyncio
async def test_bulk_statistics_acoustic_data(bulk_stats_fixture):
    # todo: to be update if it lasts too long as unit tests.
    columns_count = 1_000
    rows_count = 2_000

    cols_name_by_index = [
        ([array_col], range(rows_count)) for array_col in [f'float-{i}' for i in range(columns_count)]
    ]

    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)

    with pytest.raises(StatisticsNotFoundError):
        await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=None)

    futures = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri)
    await asyncio.gather(*futures)

    with pytest.raises(RequestedCurvesError):
        await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=['incorrect-column-name'])

    df_stats = await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=None)
    assert df_stats.shape == (columns_count, len(_bulk_stats_columns()))
