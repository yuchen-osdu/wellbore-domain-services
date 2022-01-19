# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import asyncio
from datetime import datetime, timedelta
import dask.dataframe as dd
import numpy as np
import pandas as pd

import pytest
from tests.unit.test_utils import ctx_fixture, nope_logger_fixture
from tests.unit.generate_data import generate_df
import mock

from app.utils import DaskException
from app.utils import DaskClient
from app.helper import logger
from app.persistence.sessions_storage import (Session, SessionState,
                                              SessionUpdateMode)
from app.bulk_persistence.dask.dask_bulk_storage import (BulkRecordNotFound,
                                                         BulkNotProcessable,
                                                         DaskBulkStorage)
from app.bulk_persistence.dask.dask_bulk_storage_local import make_local_dask_bulk_storage
from app.bulk_persistence.mime_types import MimeTypes
from app.bulk_persistence.dataframe_validators import no_validation




@pytest.fixture()
async def dask_storage(nope_logger_fixture, ctx_fixture, tmp_path) -> DaskBulkStorage:
    dask_storage = await make_local_dask_bulk_storage(base_directory=tmp_path)
    yield dask_storage


@pytest.fixture()
def test_session(mode=SessionUpdateMode.Overwrite) -> Session:
    utc_now = datetime.utcnow()
    return Session(id='fake_session_id', recordId='fake_record_id', fromVersion=0,
                   mode=mode, createdTime=utc_now, updatedTime=utc_now,
                   expiry=utc_now + timedelta(minutes=5),
                   state=SessionState.Open)


async def compare_frame(pdf: pd.DataFrame, ddf: dd.DataFrame):
    df = await DaskBulkStorage.client.compute(ddf)
    assert not set(pdf.columns) ^ set(df.columns) # check contains same columns
    df = df[pdf.columns]
    df.index.name = None
    pdf.index.name = None
    check_freq = True
    if isinstance(df.index, pd.DatetimeIndex):
        check_freq = False
    pd.testing.assert_frame_equal(pdf, df, check_freq=check_freq)


async def add_chunk(storage: DaskBulkStorage, session, df: pd.DataFrame):
    df_parquet_bytes = df.to_parquet()
    bulkid, _ = await storage.add_chunk_in_session(
        df_parquet_bytes,
        MimeTypes.PARQUET,
        no_validation,
        session.recordId,
        session.id)
    return bulkid


async def save_bulk(storage: DaskBulkStorage, df: pd.DataFrame, record_id, bulk_id=None):
    df_parquet_bytes = df.to_parquet()
    bulkid, _ = await storage.post_data_without_session(
        df_parquet_bytes,
        MimeTypes.PARQUET,
        no_validation,
        record_id,
        bulk_id)
    return bulkid


@pytest.mark.asyncio
async def test_save_bulk_with_bulk_id(dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    bulk_id = 'abcdef'
    record_id='test_save_bulk_with_bulk_id_record_id'
    bulk_id_returned = await save_bulk(dask_storage, df_ref, record_id=record_id, bulk_id=bulk_id)
    assert bulk_id == bulk_id_returned

    df = await dask_storage.load_bulk(record_id=record_id, bulk_id=bulk_id)
    await compare_frame(df_ref, df)


@pytest.mark.asyncio
async def test_save_bulk(dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    record_id='test_save_bulk_record_id'
    bulk_id = await save_bulk(dask_storage, df_ref, record_id=record_id)
    assert bulk_id

    df = await dask_storage.load_bulk(record_id=record_id, bulk_id=bulk_id)
    await compare_frame(df_ref, df)

    with pytest.raises(BulkRecordNotFound):
        await dask_storage.load_bulk(record_id="bad_record", bulk_id=bulk_id)


@pytest.mark.asyncio
async def test_save_blob_with_same_data_at_once(dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(100))

    record_id = 'test_save_bulk_record_id'
    concurrent_save_bulks = 5

    routines = [save_bulk(dask_storage, df_ref, record_id=f'{record_id}-{i}') for i in range(concurrent_save_bulks)]
    bulk_ids = await asyncio.gather(*routines)
    assert len(bulk_ids) == concurrent_save_bulks  # TODO I don't understand the actual goal of this test


@pytest.mark.asyncio
async def test_session_append_rows(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    for idx in range(0, 1000, 100):
        df = df_ref.iloc[idx:idx + 100]
        await add_chunk(dask_storage, test_session, df)

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_append_columns(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    for c in df_ref.columns:
        df = df_ref[[c]]
        await add_chunk(dask_storage, test_session, df)

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_update_add_new_rows(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))

    bulk_id = await save_bulk(dask_storage, df_ref.iloc[:100], record_id=test_session.recordId)

    for idx in range(100, 1000, 100):
        df = df_ref.iloc[idx:idx + 100]
        await add_chunk(dask_storage, test_session, df)

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_update_add_new_columns(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'floatB', 'strC'], range(1000))
    
    bulk_id = await save_bulk(dask_storage, df_ref[['A']], record_id=test_session.recordId)

    for c in ['floatB', 'strC']:
        df = df_ref[[c]]
        await add_chunk(dask_storage, test_session, df)

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_update_add_new_columns_shifted(test_session, dask_storage: DaskBulkStorage):
    A = generate_df(['A'], range(100))
    C = generate_df(['A', 'strC'], index=range(100, 200))
    df_ref = pd.concat([A,C])
    
    bulk_id = await save_bulk(dask_storage, A, record_id=test_session.recordId)

    await add_chunk(dask_storage, test_session, C)

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_empty_chunk(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(0))

    with pytest.raises(BulkNotProcessable):
        await add_chunk(dask_storage, test_session, df_ref)

    with pytest.raises(BulkNotProcessable):
        await save_bulk(dask_storage, df_ref, record_id=test_session.recordId)


@pytest.mark.asyncio
async def test_session_empty_session(dask_storage: DaskBulkStorage):
    with pytest.raises(BulkRecordNotFound):
        await dask_storage.load_bulk(record_id="123", bulk_id="bad_id")


@pytest.mark.asyncio
async def test_session_update_ovelap(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))

    bulk_id = await save_bulk(dask_storage, df_ref, record_id=test_session.recordId)
    
    # update A and B value for index > 500
    df_ref.loc[df_ref.index > 500, ['A']] = 1
    df_ref.loc[df_ref.index > 500, ['B']] = 2

    df_ref.loc[df_ref.index < 100, ['B']] = 3
    df_ref.loc[df_ref.index < 100, ['C']] = 4

    # update values in session
    await add_chunk(dask_storage, test_session, df_ref.loc[df_ref.index > 500, ['A', 'B']])
    await add_chunk(dask_storage, test_session, df_ref.loc[df_ref.index < 100, ['B', 'C']])

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_update_ovelap_by_column(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))

    bulk_id = await save_bulk(dask_storage, df_ref, record_id=test_session.recordId)

    # update A and B values for index > 500
    df_ref.loc[df_ref.index > 500, ['A']] = 1
    df_ref.loc[df_ref.index > 500, ['B']] = 2

    # update each column values in session
    for c in ['A', 'B']:
        await add_chunk(dask_storage, test_session, df_ref.loc[df_ref.index > 500, [c]])

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_bad_bulkId_commit(test_session, dask_storage: DaskBulkStorage):
    await add_chunk(dask_storage, test_session, generate_df(['A'], range(10)))
    with pytest.raises(BulkRecordNotFound):
        await dask_storage.session_commit(test_session, from_bulk_id="bad_bulk_id")


@pytest.mark.asyncio
async def test_empty_session_commit(test_session, dask_storage: DaskBulkStorage):
    with pytest.raises(BulkNotProcessable):
        await dask_storage.session_commit(test_session, from_bulk_id=test_session.recordId)


@pytest.mark.asyncio
async def test_bad_columns_requested(test_session, dask_storage: DaskBulkStorage):
    await add_chunk(dask_storage, test_session, generate_df(['A'], range(10)))
    bulk_id = await dask_storage.session_commit(test_session)
    await dask_storage.load_bulk(test_session.recordId, bulk_id, ['A'])
    with pytest.raises(BulkRecordNotFound):
        await dask_storage.load_bulk(test_session.recordId, bulk_id, ['B'])
    with pytest.raises(BulkRecordNotFound):
        await dask_storage.load_bulk(test_session.recordId, bulk_id, ['A', 'B'])


@pytest.mark.asyncio
async def test_load_index(test_session, dask_storage: DaskBulkStorage):
    await add_chunk(dask_storage, test_session, generate_df(['A'], range(10)))
    await add_chunk(dask_storage, test_session, generate_df(['B'], range(10, 20)))
    bulk_id = await dask_storage.session_commit(test_session)
    index = await dask_storage.load_index(test_session.recordId, bulk_id)
    expected_index = pd.Index(range(0, 20))
    assert index.equals(expected_index)


@pytest.mark.asyncio
async def test_all_type(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['dateD', 'floatB', 'intA', 'strC'], range(5))

    # test without session
    bulk_id = await save_bulk(dask_storage, df_ref, record_id=test_session.recordId)
    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)

    # test with session and chunks
    for c in df_ref:
        await add_chunk(dask_storage, test_session, df_ref[[c]])
    bulk_id = await dask_storage.session_commit(test_session)

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_index_float(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], np.arange(1, 10, 0.5))

    for c in df_ref:
        await add_chunk(dask_storage, test_session, df_ref[[c]])

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)

    df_ref = df_ref.join(generate_df(['D'], index=np.arange(0, 5, 0.25)), how="outer")
    await add_chunk(dask_storage, test_session, df_ref[['D']])
    bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_index_str(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B'], [f"str_{i}" for i in range(10)])

    # without session
    with pytest.raises(BulkNotProcessable):
        await save_bulk(dask_storage, df_ref, record_id=test_session.recordId)

    # with session
    with pytest.raises(BulkNotProcessable):
        await add_chunk(dask_storage, test_session, df_ref)


@pytest.mark.asyncio
async def test_index_time(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B'], pd.date_range("2021-01-01", periods=10, freq="min"))

    for c in df_ref:
        await add_chunk(dask_storage, test_session, df_ref[[c]])

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)

    D = generate_df(['D'], index=pd.date_range("2021-01-01", periods=30, freq="30s"))
    df_ref = df_ref.join(D, how="outer")
    await add_chunk(dask_storage, test_session, df_ref[['D']])
    bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_duplicate_index(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A'], [0, 1, 2, 2])

    # without session
    with pytest.raises(BulkNotProcessable):
        await save_bulk(dask_storage, df_ref, record_id=test_session.recordId)

    # with session
    with pytest.raises(BulkNotProcessable):
        await add_chunk(dask_storage, test_session, df_ref)


@pytest.mark.parametrize("system_memory, worker_created", [
    (42, 0),
    ((DaskClient.min_worker_memory_recommended + DaskClient.memory_leeway), 1),
    ((DaskClient.min_worker_memory_recommended * 3 + DaskClient.memory_leeway), 3),
    ((DaskClient.min_worker_memory_recommended * 3 + DaskClient.memory_leeway) + 1000, 3)
])
@pytest.mark.asyncio
async def test_dask_workers_according_ram_available(system_memory, worker_created):
    # clear existing Dask distributed client
    await DaskClient.close()
    logger._LOGGER = mock.MagicMock()

    with mock.patch('app.utils.DaskClient._get_system_memory', mock.Mock(return_value=system_memory)):
        with mock.patch('app.utils.DaskClient._recommended_workers_and_threads', mock.Mock(return_value=(10, 10))):

            if DaskClient._available_memory_for_workers() < DaskClient.min_worker_memory_recommended:
                with pytest.raises(DaskException):
                    await DaskClient.create()
            else:
                client = await DaskClient.create()
                expected_worker_memory = (system_memory - DaskClient.memory_leeway) / worker_created
                assert worker_created == len(client.cluster.scheduler.workers)

                workers_has_expected_memory = [w.memory_limit == int(expected_worker_memory)
                                               for _, w in client.cluster.scheduler.workers.items()]
                assert all(workers_has_expected_memory)

    await DaskClient.close()


@pytest.mark.asyncio
async def test_array_values(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['array_10_A', 'array_5_B', 'C'], range(5))
    assert len(df_ref['array_10_A'][0]) == 10
    bulk_id = await save_bulk(dask_storage, df_ref, record_id=test_session.recordId)

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_duplicate_chunk(test_session, dask_storage: DaskBulkStorage):
    chunk1 = generate_df(['A', 'B'], range(10))
    chunk2 = generate_df(['A', 'B'], range(10))
    chunk3 = generate_df(['A', 'B'], range(10, 20))
    chunk4 = generate_df(['C', 'D'], range(5, 15))

    await add_chunk(dask_storage, test_session, chunk1)
    await add_chunk(dask_storage, test_session, chunk2)
    await add_chunk(dask_storage, test_session, chunk3)
    await add_chunk(dask_storage, test_session, chunk4)
    
    bulk_id = await dask_storage.session_commit(test_session)
    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)

    expected_df = pd.concat([chunk2, chunk3], axis=0)
    expected_df = pd.concat([expected_df, chunk4], axis=1)

    await compare_frame(expected_df, ddf)


@pytest.mark.asyncio
async def test_named_index_chunk(test_session, dask_storage: DaskBulkStorage):
    chunk = generate_df(['A', 'B'], range(10))
    chunk['idx'] = range(10)
    chunk = chunk.set_index('idx')

    bulk_id = await save_bulk(dask_storage, chunk, test_session.recordId)
    
    stat = await dask_storage.read_stat(test_session.recordId, bulk_id)
    assert {'A', 'B'} == set(stat['schema'])

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    chunk.index.name = None
    await compare_frame(chunk, ddf)
