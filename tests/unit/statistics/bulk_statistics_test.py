import asyncio
from datetime import datetime, timedelta
import uuid
from typing import List

from unittest import mock
from unittest.mock import PropertyMock, AsyncMock

import numpy as np
import pandas as pd
import pytest

from odes_storage.models import Record, StorageAcl, Legal

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage


from app.bulk_persistence.statistics.exceptions import StatisticsNotFoundError, RequestedCurvesError, \
    ComputationRunningError

from app.bulk_persistence.statistics.models import BulkStatisticsStatus, InternalStatisticsComputationMeta
from app.consistency import NoConsistencyChecks
from tests.unit.test_utils import ctx_fixture
from tests.unit.generate_data import generate_df

from app.bulk_persistence import (Session, SessionState, SessionUpdateMode)
from app.bulk_persistence.dask.client import actx as dask_client_actx
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.statistics.bulk_statistics import BulkStatistics, grouper, get_columns_count
from app.bulk_persistence.dask.dask_bulk_storage_local import make_local_dask_bulk_storage
from app.bulk_persistence import MimeTypes
from app.bulk_persistence.dataframe_validators import no_validation


pytestmark = pytest.mark.statistics


@pytest.mark.parametrize("container", [
    list(),
    list(range(10))
])
@pytest.mark.parametrize("step,expected_values", [
    (0, []),
    (2.8, [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]),
    (3, [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)]),
    (6, [(0, 1, 2, 3, 4, 5), (6, 7, 8, 9)]),
    (10, [(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)]),
    (11, [(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)]),
])
def test_grouper(container, step, expected_values):
    result = list(grouper(step, container))
    for r in result:
        assert len(r) <= min(step, len(container))

    if container:
        assert result == expected_values


@pytest.mark.parametrize("container", [
    list(range(10)),
    list()
])
@pytest.mark.parametrize("step", [-10, "string value", -10.8])
def test_grouper_incorrect_value(container, step):
    with pytest.raises(ValueError):
        list(grouper(step, container))


@pytest.mark.parametrize("max_columns_count, nb_rows, nb_cols, expected", [
    (100, 10, 10, 10),
    (100, 100, 10, 1),
    (100, 1000, 10, 1),

    (10, 2, 100, 10),
])
def test_get_columns_count(max_columns_count, nb_rows, nb_cols, expected):
    max_number_values = 100

    result = get_columns_count(max_number_values, max_columns_count, nb_rows, nb_cols)
    assert result == expected


@pytest.fixture
async def bulk_stats_fixture(dask_custom_config, tmp_path, nope_logger_fixture, ctx_fixture,
                             local_bulk_persistence_config) -> (BulkStatistics, DaskBulkStorage):
    with dask_custom_config():
        async with dask_client_actx(local_bulk_persistence_config) as client:

            local_dask = await make_local_dask_bulk_storage(str(tmp_path),
                                                            local_bulk_persistence_config,
                                                            dask_client=client)

            async def _blob_storage_builder():
                return LocalFSBlobStorage(str(tmp_path))

            ctx_fixture.app_injector.register(BlobStorageBase, _blob_storage_builder)

            bulk_stats = BulkStatistics(dask_blob_storage=local_dask)

            bulk_stats._paging_size_per_batch = 500_000
            bulk_stats._max_cols_per_batch = 100
            yield bulk_stats, local_dask

            ctx_fixture.app_injector.register(BlobStorageBase, AsyncMock())


def _add_nan_values_in_df(chunk_df):
    cols_with_nan = [c for c in chunk_df.columns if c.endswith('nan')]
    for col_with_nan in cols_with_nan:
        chunk_df.loc[chunk_df.sample(frac=0.1).index, col_with_nan] = np.nan


async def add_bulk_data_by_chunks_to_fixture(dask_blob_storage, cols_with_index: List[tuple]):
    session = create_test_bulk_session()
    coroutines = []
    for columns_name, values_index in cols_with_index:
        chunk_df = generate_df(columns_name, values_index)

        _add_nan_values_in_df(chunk_df)

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


def extract_distinct_cols(cols_name_by_index):
    """ Extract distinct columns from input test cases"""
    all_cols = []
    for requested_cols, _ in cols_name_by_index:
        all_cols.extend(requested_cols)

    distinct_cols = set(all_cols)
    valid_cols = [c for c in distinct_cols
                  if not c.startswith('bool') and not c.startswith('string')]

    assert valid_cols, "At least one column needs to be valid for test cases below"
    return valid_cols


def create_test_bulk_session() -> Session:
    record_id = "my-record-id"
    session_id = uuid.uuid4()

    session = Session(id=session_id,
                      recordId=record_id,
                      fromVersion='123456',
                      mode=SessionUpdateMode.Overwrite,
                      expiry=datetime.now(),
                      createdTime=datetime.now(),
                      updatedTime=datetime.now(),
                      state=SessionState.Open
                      )
    return session


def _bulk_stats_columns() -> List[str]:
    """
        Return the expected list of columns of bulk stats
    """
    return sorted(['nonAbsentValuesCount', 'mean', 'min', '10%', '50%', '90%', 'max', 'std', 'totalCount'])


def _bulk_stats_columns_if_date_type_only() -> List[str]:
    """
        # If there is only date, 'std' (standard deviation) is NaN then ignored from result
    """
    columns = _bulk_stats_columns()
    columns.remove('std')
    return columns


@pytest.mark.anyio
@pytest.mark.parametrize("cols_name_by_index, returned_curves_count, expected_cols", [
    (
            # check common type of data types => check only integer, float and date are compatible.
            [(['int-A', 'float-B', 'date-C', 'bool-D', 'string-E'], range(500))], 3, _bulk_stats_columns()
    ),
    (
            # ensure data by only datetime is correctly processed
            [(['date-C', 'date-D'], range(100))], 2, _bulk_stats_columns()
    ),
    (
            # Check fetching and compute stats by batch of bulk is working properly one chunk data
            [(['int-A', 'float-B', 'date-C'], range(400_000))], 3, _bulk_stats_columns()
    ),
    (
            # Check fetching and compute stats by batch of bulk is working properly with chunked data
            [
                (['float-A', 'float-B', 'float-C'], range(100_000)),
                (['float-A', 'float-B', 'float-C'], range(100_000, 200_000)),
                (['float-A', 'float-B', 'float-C'], range(400_000, 500_000)),
                (['float-A', 'float-B', 'float-C'], range(500_000, 600_000)),
            ],
            3, _bulk_stats_columns()
    ),
])
async def test_bulk_statistics_get_bulk_statistics(bulk_stats_fixture, cols_name_by_index,
                                                   returned_curves_count, expected_cols):
    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)
    catalog = await dask_storage.get_bulk_catalog(record_id, bulk_uri)

    fake_record_id = 123456789
    with pytest.raises(StatisticsNotFoundError):
        await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=None)

    future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri, record_version=fake_record_id)
    await future

    df_stats, stats_meta = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=None)
    assert len(df_stats) == returned_curves_count
    assert sorted(list(df_stats.columns)) == expected_cols

    assert stats_meta.record_id == record_id
    assert stats_meta.record_version == fake_record_id
    assert stats_meta.computation_status == BulkStatisticsStatus.Complete

    now = datetime.utcnow()
    assert now - timedelta(seconds=3) < stats_meta.computation_start_datetime < now + timedelta(seconds=3)


@pytest.mark.anyio
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
async def test_bulk_statistics_get_statistics_invalid_cols(bulk_stats_fixture, cols_name_by_index, expected_shape):
    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)
    catalog = await dask_storage.get_bulk_catalog(record_id, bulk_uri)

    valid_cols = extract_distinct_cols(cols_name_by_index)

    future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri, record_version=123456789)
    await future

    with pytest.raises(RequestedCurvesError):
        await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=['incorrect-column-name'])

    computable_col_plus_invalid_cols = [valid_cols[0], 'incorrect-column-name']
    with pytest.raises(RequestedCurvesError):
        await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=computable_col_plus_invalid_cols)

    not_computable_cols = ['bool-D', 'string-E']
    result_df_1, stats_meta = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri,
                                                                        columns=not_computable_cols)
    assert result_df_1.empty


@pytest.mark.anyio
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
async def test_bulk_statistics_get_statistics_mix_requested_cols(bulk_stats_fixture, cols_name_by_index, expected_shape):
    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)
    catalog = await dask_storage.get_bulk_catalog(record_id, bulk_uri)

    computable_cols = extract_distinct_cols(cols_name_by_index)

    future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri, record_version=123456789)
    await future

    not_computable_cols = ['bool-D', 'string-E']
    not_computable_cols_plus_valid_cols = not_computable_cols + [computable_cols[0]]
    result_df_2, stats_meta = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri,
                                                                        columns=not_computable_cols_plus_valid_cols)
    assert result_df_2.shape == (1, 9)
    assert result_df_2.index == [computable_cols[0]]


@pytest.mark.anyio
@pytest.mark.parametrize("cols_name_by_index, expected_shape", [
    (
            [(['int-A-nan', 'float-B', 'date-C-nan', 'bool-D', 'string-E'], range(500))],
            (3, len(_bulk_stats_columns_if_date_type_only()))
    ),
])
async def test_bulk_statistics_nan_columns(bulk_stats_fixture, cols_name_by_index, expected_shape):
    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)
    catalog = await dask_storage.get_bulk_catalog(record_id, bulk_uri)

    computable_cols = extract_distinct_cols(cols_name_by_index)
    nan_cols = [c for c in computable_cols if 'nan' in c]

    future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri, record_version=123456789)
    await future

    result_df_with_nan_cols, _ = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=None)
    assert result_df_with_nan_cols.shape == (len(computable_cols), 9)
    assert sorted(list(result_df_with_nan_cols.index)) == sorted(computable_cols)

    all_valid_result_df, _ = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=computable_cols)
    assert sorted(list(all_valid_result_df.index)) == sorted(computable_cols)

    nan_cols_df = all_valid_result_df.filter(items=nan_cols, axis=0)
    total_count = list(nan_cols_df[BulkStatistics._valid_values_label].astype(int))
    non_absent_values_count = list(nan_cols_df[BulkStatistics._renaming_stats_labels['count']].astype(float))
    assert total_count > non_absent_values_count


@pytest.mark.anyio
@pytest.mark.statistics
@pytest.mark.perf
@pytest.mark.skip("This test if skipped for unit testing, it should be run for performances instead")
async def test_bulk_statistics_acoustic_data(bulk_stats_fixture):
    columns_count = 1_000
    rows_count = 2_000

    cols_name_by_index = [
        ([array_col], range(rows_count)) for array_col in [f'float-{i}' for i in range(columns_count)]
    ]

    bulk_statistics, dask_storage = bulk_stats_fixture
    record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, cols_name_by_index)
    catalog = await dask_storage.get_bulk_catalog(record_id, bulk_uri)

    with pytest.raises(StatisticsNotFoundError):
        await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=None)

    future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri, record_version=123456789)
    await future

    with pytest.raises(RequestedCurvesError):
        await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=['incorrect-column-name'])

    df_stats, stats_meta = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_uri, columns=None)
    assert df_stats.shape == (columns_count, len(_bulk_stats_columns()))

import anyio
@pytest.mark.anyio
async def test_trigger_computations_after_error(bulk_stats_fixture):

    async def _compute_stats_on_bulk_batch(n):
        if n % 2 == 0:
            raise Exception("test_get_stats_if_error")
    tasks = [asyncio.get_event_loop().create_task(_compute_stats_on_bulk_batch(i)) for i in range(5)]

    with mock.patch.object(BulkStatistics, 'trigger_stats_computation_in_dask') as bob:
        bob.return_value = tasks

        bulk_statistics, dask_storage = bulk_stats_fixture
        columns_indexes = [(['int-A', 'float-B', 'date-C', 'bool-D', 'string-E'], range(500))]
        record_id, bulk_uri = await add_bulk_data_by_chunks_to_fixture(dask_storage, columns_indexes)

        for i in range(1, 4):
            future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri, record_version=123456)
            result: InternalStatisticsComputationMeta = await future
            assert result.meta.computation_status == BulkStatisticsStatus.Error
            assert result.computation_attempt == i
            now = datetime.utcnow()
            assert now - timedelta(seconds=1) < result.last_computation_date < now + timedelta(seconds=1)

        with pytest.raises(ComputationRunningError, match="Statistics computation has already failed 3 times. ABORT"):
            await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri, record_version=123456)


@pytest.mark.anyio
async def test_computations_values(bulk_stats_fixture):
    with mock.patch.object(BulkStatistics, '_max_cols_per_batch', new_callable=PropertyMock) \
            as computations_parameter:
        computations_parameter.return_value = 1

        bulk_statistics, dask_storage = bulk_stats_fixture

        values_count = 500
        bulk_df = pd.DataFrame({
            'int-A': np.arange(-100, 400, step=1, dtype=int),
            'int-A-nan': np.arange(-100, 1400, step=3, dtype=int),
            'float-B': np.arange(-100, 650, step=1.5, dtype=float),
            'float-B-nan': np.arange(-100, 1550, step=3.3, dtype=float),
            'date-C': pd.date_range(start='1/1/2022', freq='s', periods=values_count),
            'date-C-nan': pd.date_range(start='1/1/2022', freq='D', periods=values_count),
            'bool-D': [i % 2 == 0 for i in range(values_count)],
            'string-E': [f'string_value_{i}' for i in range(values_count)],
        })
        _add_nan_values_in_df(bulk_df)

        bulk_id = str(uuid.uuid4())
        record_id = "MyRecordTestID"
        await dask_storage.post_data_without_session(data=bulk_df.to_parquet(engine='pyarrow'),
                                                     content_type=MimeTypes.PARQUET,
                                                     df_validator_func=no_validation,
                                                     consistency_checks=NoConsistencyChecks,
                                                     record=Record(id=record_id, kind="",
                                                                   acl=StorageAcl(viewers=[], owners=[]), legal=Legal(),
                                                                   data={}),
                                                     bulk_id=bulk_id,
                                                     )

        future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_id, record_version=123456)
        await future

        catalog = await dask_storage.get_bulk_catalog(record_id, bulk_id)
        stats_df, stats_meta = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_id, columns=None)

        expected_stats_df = bulk_df.describe(datetime_is_numeric=True, percentiles=[.10, .5, .90])
        expected_stats_df = expected_stats_df.astype('string').transpose()
        expected_stats_df['totalCount'] = str(values_count)
        expected_stats_df.rename(columns={'count': 'nonAbsentValuesCount'}, inplace=True)

        pd.testing.assert_frame_equal(stats_df, expected_stats_df, check_like=True)


@pytest.mark.anyio
async def test_computations_not_computable_values(bulk_stats_fixture):
    with mock.patch.object(BulkStatistics, '_max_cols_per_batch', new_callable=PropertyMock) \
            as computations_parameter:
        computations_parameter.return_value = 1

        bulk_statistics, dask_storage = bulk_stats_fixture

        values_count = 10
        bulk_df = pd.DataFrame({
            'bool-D': [i % 2 == 0 for i in range(values_count)],
            'string-E': [f'string_value_{i}' for i in range(values_count)],
        })
        _add_nan_values_in_df(bulk_df)

        bulk_id = str(uuid.uuid4())
        record_id = "MyRecordTestID"
        await dask_storage.post_data_without_session(data=bulk_df.to_parquet(engine='pyarrow'),
                                                     content_type=MimeTypes.PARQUET,
                                                     df_validator_func=no_validation,
                                                     consistency_checks=NoConsistencyChecks,
                                                     record=Record(id=record_id, kind="",
                                                                   acl=StorageAcl(viewers=[], owners=[]), legal=Legal(),
                                                                   data={}),
                                                     bulk_id=bulk_id,
                                                     )

        future = await bulk_statistics.compute_bulk_statistics(record_id, bulk_id, record_version=123456)
        await future

        catalog = await dask_storage.get_bulk_catalog(record_id, bulk_id)
        stats_df, stats_meta = await bulk_statistics.get_bulk_statistics(catalog, record_id, bulk_id, columns=None)

        expected_empty_stats_df = pd.DataFrame()
        pd.testing.assert_frame_equal(stats_df, expected_empty_stats_df)
