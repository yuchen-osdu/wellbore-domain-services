import asyncio
import datetime

import mock
import pandas as pd
import pytest

from app.bulk_persistence.statistics.exceptions import StatisticsNotFoundError, RequestedCurvesError
from tests.unit.test_utils import ctx_fixture

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
def app_initialized_with_testclient(local_dev_config, dask_client):
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
    yield BulkStatistics(dask_blob_storage=local_dask), local_dask
    local_dask.client.close()


@pytest.fixture()
async def bulk_stats_fixture_with_data(bulk_stats_fixture):
    bulk_statistics, dask_blob_storage = bulk_stats_fixture
    session = create_test_session()

    from tests.unit.generate_data import generate_df
    import numpy as np
    def generate_df_typed(columns, index):

        def gen_values(col_name, size):
            if col_name.startswith('float'):
                return np.random.random_sample(size=size)
            if col_name.startswith('str'):
                return [f'string_value_{i}' for i in range(size)]
            if col_name.startswith('bool'):
                return np.random.choice(a=[False, True], size=size)
            if col_name.startswith('date'):
                return pd.date_range(start='1/1/2022', periods=size)
            return np.random.randint(-100, 1000, size=size)

        df = pd.DataFrame({c: gen_values(c, len(index))
                           for c in columns}, index=index)
        return df

    typed_df = generate_df_typed(['int-A', 'float-B', 'date-C', 'bool-D', 'string-E'], range(500))
    parquet_data = typed_df.to_parquet(engine='pyarrow')

    await dask_blob_storage.add_chunk_in_session(parquet_data, MimeTypes.PARQUET, no_validation, session.recordId, session.id)
    new_bulk_id = await dask_blob_storage.session_commit(session)
    assert new_bulk_id

    yield bulk_statistics, session.recordId, new_bulk_id

    # bob = await dask_blob_storage.load_bulk(session.recordId, new_bulk_id)
    # print(bob)


def create_test_session() -> Session:
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


# @pytest.mark.asyncio
# async def test_bulk_statistics_compute_bulk_statistics(bulk_stats_fixture: BulkStatistics):
#     record_id = "incorrect-record-id"
#     bulk_uri = ""
#
#     bulk_statistics, _ = bulk_stats_fixture
#     from app.bulk_persistence.dask.errors import BulkRecordNotFound
#     with pytest.raises(BulkRecordNotFound):
#         await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri)


@pytest.mark.asyncio
async def test_bulk_statistics_get_bulk_statistics(bulk_stats_fixture_with_data: BulkStatistics):
    bulk_statistics, record_id, bulk_uri = bulk_stats_fixture_with_data

    with pytest.raises(StatisticsNotFoundError):
        await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=None)

    futures = await bulk_statistics.compute_bulk_statistics(record_id, bulk_uri)
    await asyncio.gather(*futures)

    with pytest.raises(RequestedCurvesError):
        await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=['incorrect-column-name'])

    df_stats = await bulk_statistics.get_bulk_statistics(record_id, bulk_uri, columns=None)
    # raise RequestedCurvesError("Requested curves unknown")
    assert len(df_stats.columns) == 8
    assert len(df_stats) == 3