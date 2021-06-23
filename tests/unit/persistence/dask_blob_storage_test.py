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
from tempfile import TemporaryDirectory

import dask.dataframe as dd
import numpy as np
import pandas as pd
import pytest
from app.bulk_persistence.dask.dask_bulk_storage import (BulkNotFound,
                                                         BulkNotProcessable,
                                                         DaskBulkStorage,
                                                         make_local_dask_bulk_storage)
from app.persistence.sessions_storage import (Session, SessionState,
                                              SessionUpdateMode)

from tests.unit.test_utils import ctx_fixture, nope_logger_fixture


def generate_df(columns, index):
    def gen_values(col_name, size):
        if col_name.startswith('float'):
            return np.random.random_sample(size=size)
        if col_name.startswith('str'):
            return [f'string_value_{i}' for i in range(size)]
        if col_name.startswith('date'):
            return (np.datetime64('2021-01-01') + days for days in range(size))
        return np.random.randint(-100, 1000, size=size)

    df = pd.DataFrame({c: gen_values(c, len(index))
                       for c in columns}, index=index)
    return df


@pytest.fixture(scope="module")
def event_loop():  # all tests will share the same loop
    loop = asyncio.get_event_loop()
    yield loop
    # teardown
    loop.run_until_complete(DaskBulkStorage.close())
    loop.close()


@pytest.fixture()
async def dask_storage(nope_logger_fixture, ctx_fixture) -> DaskBulkStorage:
    with TemporaryDirectory() as tmp_dir:
        dask_storage = await make_local_dask_bulk_storage(base_directory=tmp_dir)
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
    df.index.name = None
    check_freq = True
    if isinstance(df.index, pd.DatetimeIndex):
        check_freq = False
    pd.testing.assert_frame_equal(pdf, df, check_freq=check_freq)


@pytest.mark.asyncio
async def test_save_blob_with_bulk_id(dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    bulk_id = 'abcdef'
    record_id='test_save_blob_with_bulk_id_record_id'
    bulk_id_returned = await dask_storage.save_blob(df_ref, record_id=record_id, bulk_id=bulk_id)
    assert bulk_id == bulk_id_returned

    df = await dask_storage.load_bulk(record_id=record_id, bulk_id=bulk_id)
    await compare_frame(df_ref, df)


@pytest.mark.asyncio
async def test_save_blob(dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    record_id='test_save_blob_record_id'
    bulk_id = await dask_storage.save_blob(df_ref, record_id=record_id)
    assert bulk_id

    df = await dask_storage.load_bulk(record_id=record_id, bulk_id=bulk_id)
    await compare_frame(df_ref, df)

    with pytest.raises(BulkNotFound):
        await dask_storage.load_bulk(record_id="bad_record", bulk_id=bulk_id)


@pytest.mark.asyncio
async def test_session_append_rows(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    for idx in range(0, 1000, 100):
        df = df_ref.iloc[idx:idx + 100]
        await dask_storage.session_add_chunk(test_session, df)

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_append_columns(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))
    for c in df_ref.columns:
        df = df_ref[[c]]
        await dask_storage.session_add_chunk(test_session, df)

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_update_add_new_rows(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))

    bulk_id = await dask_storage.save_blob(df_ref.iloc[:100], record_id=test_session.recordId)

    for idx in range(100, 1000, 100):
        df = df_ref.iloc[idx:idx + 100]
        await dask_storage.session_add_chunk(test_session, df)

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_update_add_new_columns(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'floatB', 'strC'], range(1000))
    
    bulk_id = await dask_storage.save_blob(df_ref[['A']], record_id=test_session.recordId)

    for c in ['floatB', 'strC']:
        df = df_ref[[c]]
        await dask_storage.session_add_chunk(test_session, df)

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_empty_chunk(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(0))

    with pytest.raises(BulkNotProcessable):
        await dask_storage.session_add_chunk(test_session, df_ref)

    with pytest.raises(BulkNotProcessable):
        await dask_storage.save_blob(df_ref, record_id=test_session.recordId)


@pytest.mark.asyncio
async def test_session_empty_session(dask_storage: DaskBulkStorage):
    with pytest.raises(BulkNotFound):
        await dask_storage.load_bulk(record_id="123", bulk_id="bad_id")


@pytest.mark.asyncio
async def test_session_update_ovelap(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))

    bulk_id = await dask_storage.save_blob(df_ref, record_id=test_session.recordId)
    
    # update A and B value for index > 500
    df_ref.loc[df_ref.index > 500, ['A']] = 1
    df_ref.loc[df_ref.index > 500, ['B']] = 2

    df_ref.loc[df_ref.index < 100, ['B']] = 3
    df_ref.loc[df_ref.index < 100, ['C']] = 4

    # update values in session
    await dask_storage.session_add_chunk(test_session, df_ref.loc[df_ref.index > 500, ['A', 'B']])
    await dask_storage.session_add_chunk(test_session, df_ref.loc[df_ref.index < 100, ['B', 'C']])

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_session_update_ovelap_by_column(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], range(1000))

    bulk_id = await dask_storage.save_blob(df_ref, record_id=test_session.recordId)

    # update A and B values for index > 500
    df_ref.loc[df_ref.index > 500, ['A']] = 1
    df_ref.loc[df_ref.index > 500, ['B']] = 2

    # update each column values in session
    for c in ['A', 'B']:
        await dask_storage.session_add_chunk(
            test_session, df_ref.loc[df_ref.index > 500, [c]])

    new_bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)
    assert bulk_id != new_bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, new_bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_bad_bulkId_commit(test_session, dask_storage: DaskBulkStorage):
    with pytest.raises(BulkNotFound):
        await dask_storage.session_commit(test_session, from_bulk_id="bad_bulk_id")


@pytest.mark.asyncio
async def test_all_type(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['dateD', 'floatB', 'intA', 'strC'], range(5))

    # test without session
    bulk_id = await dask_storage.save_blob(df_ref, record_id=test_session.recordId)
    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)

    # test with session and chunks
    for c in df_ref:
        await dask_storage.session_add_chunk(test_session, df_ref[[c]])
    bulk_id = await dask_storage.session_commit(test_session)

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_index_float(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B', 'C'], np.arange(1, 10, 0.5))

    for c in df_ref:
        await dask_storage.session_add_chunk(test_session, df_ref[[c]])

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)

    df_ref = df_ref.join(generate_df(['D'], index=np.arange(0, 5, 0.25)), how="outer")
    await dask_storage.session_add_chunk(test_session, df_ref[['D']])
    bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_index_str(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B'], [f"str_{i}" for i in range(10)])

    # without session
    with pytest.raises(BulkNotProcessable):
        await dask_storage.save_blob(df_ref, record_id=test_session.recordId)

    # with session
    with pytest.raises(BulkNotProcessable):
        await dask_storage.session_add_chunk(test_session, df_ref)


@pytest.mark.asyncio
async def test_index_time(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A', 'B'], pd.date_range("2021-01-01", periods=10, freq="min"))

    for c in df_ref:
        await dask_storage.session_add_chunk(test_session, df_ref[[c]])

    bulk_id = await dask_storage.session_commit(test_session)
    assert bulk_id

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)

    D = generate_df(['D'], index=pd.date_range("2021-01-01", periods=30, freq="30s"))
    df_ref = df_ref.join(D, how="outer")
    await dask_storage.session_add_chunk(test_session, df_ref[['D']])
    bulk_id = await dask_storage.session_commit(test_session, from_bulk_id=bulk_id)

    ddf = await dask_storage.load_bulk(test_session.recordId, bulk_id)
    await compare_frame(df_ref, ddf)


@pytest.mark.asyncio
async def test_duplicate_index(test_session, dask_storage: DaskBulkStorage):
    df_ref = generate_df(['A'], [0, 1, 2, 2])

    # without session
    with pytest.raises(BulkNotProcessable):
        await dask_storage.save_blob(df_ref, record_id=test_session.recordId)

    # with session
    with pytest.raises(BulkNotProcessable):
        await dask_storage.session_add_chunk(test_session, df_ref)
