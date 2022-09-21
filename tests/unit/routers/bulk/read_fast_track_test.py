import asyncio
import uuid
from io import BytesIO

import pandas as pd
from fastapi import HTTPException

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from app.bulk_persistence import BulkCatalog, MimeTypes, BulkReadFilters, BulkFilter, BulkReadFilterOperator
from app.bulk_persistence.dask import storage_path_builder
from app.bulk_persistence.dask.bulk_catalog import BulkCatalogOrigin, ChunkGroup
from app.bulk_persistence.dask.session_file_meta import generate_chunk_filename
from app.routers.bulk import read_fast_track as ft

import pytest
from unittest.mock import AsyncMock, Mock
from pandas.testing import assert_frame_equal
from tests.unit.test_utils import ctx_fixture
from tests.unit.generate_data import generate_df
from tests.unit.blob_storage_fsspec import BlobStorageFsspec


@pytest.mark.asyncio
async def test_forward_parquet(nope_logger_fixture):
    storage_mock = Mock()
    storage_mock.download = AsyncMock(return_value=b'fake data')

    result = await ft._forward_parquet(storage_mock, Mock(), Mock())

    assert result.media_type == "application/x-parquet"
    assert result.body == b'fake data'


def test_split_dataframe_iloc(nope_logger_fixture):
    df = generate_df(['A'], index=range(10))

    assert_frame_equal(df, ft._split_dataframe_iloc(df))

    actual_df = ft._split_dataframe_iloc(df, offset=2)
    assert_frame_equal(df.iloc[2:], actual_df)
    # just double check
    assert actual_df.shape == (8, 1)
    assert actual_df.index[0] == 2

    actual_df = ft._split_dataframe_iloc(df, limit=5)
    assert_frame_equal(df.iloc[:5], actual_df)
    assert actual_df.shape == (5, 1)
    assert actual_df.index[0] == 0

    actual_df = ft._split_dataframe_iloc(df, offset=2, limit=5)
    assert_frame_equal(df.iloc[2:7], actual_df)
    assert actual_df.shape == (5, 1)
    assert actual_df.index[0] == 2


@pytest.mark.asyncio
async def test_build_response_parquet_df(nope_logger_fixture):
    df = generate_df(['B', 'C', 'A'], index=range(6))

    result = await ft._build_response_parquet_df(df, requested_columns=['A', 'C'])
    assert result.media_type == "application/x-parquet"
    actual_df = pd.read_parquet(BytesIO(result.body))
    assert_frame_equal(df[['A', 'C']], actual_df)  # column same order as requested

    result = await ft._build_response_parquet_df(df)
    assert result.media_type == "application/x-parquet"
    actual_df = pd.read_parquet(BytesIO(result.body))
    assert_frame_equal(df[['A', 'B', 'C']], actual_df)  # column in natural order


@pytest.mark.asyncio
async def test_build_response_parquet_big_df(nope_logger_fixture):
    df = generate_df(['B', 'C', 'A'], index=range(350_000))
    result = await ft._build_response_parquet_df(df)
    assert result.media_type == "application/x-parquet"
    actual_df = pd.read_parquet(BytesIO(result.body))
    assert_frame_equal(df[['A', 'B', 'C']], actual_df)  # column in natural order


@pytest.mark.asyncio
async def test_load_dataframe_from_storage(nope_logger_fixture):
    df = generate_df(['B', 'C', 'A'], index=range(6))

    storage_mock = Mock()
    storage_mock.download = AsyncMock(return_value=df.to_parquet(index=True))
    actual_df = await ft._load_dataframe_from_storage(storage_mock, tenant=Mock(), obj_path="mock")
    assert_frame_equal(df, actual_df)

    assert_frame_equal(
        df[['A', 'B']],
        await ft._load_dataframe_from_storage(storage_mock, tenant=Mock(), obj_path="mock", columns=['A', 'B'])
    )

    assert_frame_equal(
        df.iloc[4:],
        await ft._load_dataframe_from_storage(storage_mock, tenant=Mock(), obj_path="mock", offset=4)
    )

    assert_frame_equal(
        df.iloc[:3],
        await ft._load_dataframe_from_storage(storage_mock, tenant=Mock(), obj_path="mock", limit=3)
    )

    assert_frame_equal(
        df.iloc[1: 4],
        await ft._load_dataframe_from_storage(storage_mock, tenant=Mock(), obj_path="mock", offset=1, limit=3)
    )

    assert_frame_equal(
        df[['A', 'B']].iloc[1: 4],
        await ft._load_dataframe_from_storage(
            storage_mock, tenant=Mock(), obj_path="mock", columns=['A', 'B'], offset=1, limit=3)
    )


@pytest.mark.asyncio
async def test_unsupported_cases_raise(nope_logger_fixture):
    supported_filters = BulkReadFilters([])
    supported_format = MimeTypes.PARQUET

    # only PARQUET
    with pytest.raises(ft.ReadFastTrackCaseNotSupportedException):
        await ft.read_data_fast_track(Mock(), BulkCatalog(''), MimeTypes.JSON, supported_filters)

    # no filters
    with pytest.raises(ft.ReadFastTrackCaseNotSupportedException):
        await ft.read_data_fast_track(Mock(), BulkCatalog(''), supported_format,
                                      BulkReadFilters([BulkFilter('MD', BulkReadFilterOperator.Greater, '10')]))

    # single file but save by multi partitions Dask, like conflict resolution on commit session
    with pytest.raises(ft.ReadFastTrackCaseNotSupportedException):
        # TODO there's might be more rigorous way, but for now just redo what is done
        #  DaskBulkStorage._resolve_conflict_catalog
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.from_file())
        merged_df_path = storage_path_builder.join("commit_path", f'{uuid.uuid4()}.parquet')
        relative_paths = [
            storage_path_builder.record_relative_path("base_path", "record_id", merged_df_path)
        ]
        chunk_group = ChunkGroup(labels={"A"}, paths=relative_paths, dtypes=["int"])
        catalog.change_columns_info(chunk_group)
        assert catalog.chunk_count == 1
        await ft.read_data_fast_track(AsyncMock(), catalog, supported_format, supported_filters)

    # multi files, previous Dask storage (no catalog)
    with pytest.raises(ft.ReadFastTrackCaseNotSupportedException):
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
        catalog.add_chunk(ChunkGroup({'A', 'B'}, ["path1", "path2"], ["Int32"]))
        assert catalog.chunk_count > 1
        await ft.read_data_fast_track(AsyncMock(), catalog, supported_format, supported_filters)

    # chunks are not vertically slided - 1
    with pytest.raises(ft.ReadFastTrackCaseNotSupportedException):
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
        catalog.add_chunk(ChunkGroup({'A'}, ['path1', 'paths2'], ["Int32"]))
        await ft.read_data_fast_track(AsyncMock(), catalog, supported_format, supported_filters)

    # chunks are not vertically slided - 2
    with pytest.raises(ft.ReadFastTrackCaseNotSupportedException):
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
        catalog.add_chunk(ChunkGroup({'A'}, ['path1'], ["Int32"]))
        catalog.add_chunk(ChunkGroup({'A', 'B'}, ['paths2'], ["Int32"]))
        await ft.read_data_fast_track(AsyncMock(), catalog, supported_format, supported_filters)


@pytest.mark.asyncio
async def test_request_too_many_column_raise(nope_logger_fixture):
    catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
    catalog.add_chunk(ChunkGroup({f'C[{i}]' for i in range(5001)}, ["path1"], []))
    args = [AsyncMock(), catalog, MimeTypes.PARQUET, BulkReadFilters([])]

    # read all
    with pytest.raises(HTTPException) as ex_info:
        await ft.read_data_fast_track(*args, curves_selection=None)
    assert ex_info.value.status_code == 400

    # read 3000+ columns
    curve_selection = [f'C[{i}]' for i in range(1000, 4001)]
    with pytest.raises(HTTPException) as ex_info:
        await ft.read_data_fast_track(*args, curves_selection=curve_selection)
    assert ex_info.value.status_code == 400

    # read 3000+ columns even with limit
    with pytest.raises(HTTPException) as ex_info:
        await ft.read_data_fast_track(*args, curves_selection=curve_selection, offset=10, limit=1)
    assert ex_info.value.status_code == 400


@pytest.mark.asyncio
async def test_request_too_many_values_raise(nope_logger_fixture):
    catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
    catalog.add_chunk(ChunkGroup({f'C[{i}]' for i in range(100)}, ["path1"], []))
    catalog.nb_rows = 1_000_000
    args = [AsyncMock(), catalog, MimeTypes.PARQUET, BulkReadFilters([])]

    # request 6M
    with pytest.raises(HTTPException) as ex_info:
        await ft.read_data_fast_track(*args, curves_selection=[f'C[{i}]' for i in range(6)])
    assert ex_info.value.status_code == 400

    # request 4M but need to work on a 100M dataframe
    with pytest.raises(HTTPException) as ex_info:
        await ft.read_data_fast_track(*args, limit=40_000)
    assert ex_info.value.status_code == 400


@pytest.fixture
async def local_blob_path(tmp_path_factory):
    return str(tmp_path_factory.mktemp(basename="blob-"))


@pytest.fixture
async def bulk_storage_mock(ctx_fixture, tmp_path_factory):
    local_blob_path = str(tmp_path_factory.mktemp(basename="blob-"))
    blob_storage = BlobStorageFsspec(local_blob_path, 'file', auto_mkdir=True)

    async def _storage_mock(*_, **__):
        return blob_storage

    ctx_fixture.app_injector.register(BlobStorageBase, _storage_mock)
    return blob_storage


async def store_chunks(storage: BlobStorageBase, tenant, chunks) -> BulkCatalog:
    catalog = BulkCatalog('r_id', origin=BulkCatalogOrigin.from_file())
    for df in chunks:
        chunk_filename = generate_chunk_filename(df) + '.parquet'
        chunk_path = storage_path_builder.join(storage_path_builder.record_path('', catalog.record_id), chunk_filename)
        catalog.add_chunk(ChunkGroup(set(df.columns), [chunk_filename], []))
        await storage.upload(tenant, chunk_path, df.to_parquet(None, index=True))
    return catalog


async def assert_fast_track(ctx, catalog, expected_df, offset=None, limit=None, columns=None):
    # WHEN read full bulk
    response = await ft.read_data_fast_track(ctx, catalog, MimeTypes.PARQUET, BulkReadFilters([]),
                                             offset=offset, limit=limit, curves_selection=columns)

    # THEN
    actual_df = pd.read_parquet(BytesIO(response.body))
    assert_frame_equal(expected_df, actual_df)


@pytest.mark.asyncio
async def test_single_chunk_case(nope_logger_fixture, ctx_fixture, bulk_storage_mock):
    # GIVEN single chunk stored
    reference_df = generate_df(['B', 'C', 'A'], index=range(6))
    catalog = await store_chunks(bulk_storage_mock, ctx_fixture.tenant, [reference_df])
    catalog.nb_rows = len(reference_df.index)

    # WHEN read full bulk
    await assert_fast_track(ctx_fixture, catalog, reference_df)

    # WHEN read all columns, ensure column order
    await assert_fast_track(ctx_fixture, catalog, reference_df[['C', 'B', 'A']], columns=['C', 'B', 'A'])

    # WHEN read one column
    await assert_fast_track(ctx_fixture, catalog, reference_df[['A']], columns=['A'])

    # WHEN read few columns, offset, limit
    await assert_fast_track(ctx_fixture, catalog, reference_df[['A']].iloc[1:3], columns=['A'], offset=1, limit=2)


@pytest.mark.asyncio
async def test_multi_chunk_case(nope_logger_fixture, ctx_fixture, bulk_storage_mock):
    # GIVEN df split into 2 chunks
    reference_df = generate_df(['A', 'B', 'C', 'D', 'E'], index=range(6))
    catalog = await store_chunks(bulk_storage_mock, ctx_fixture.tenant, [
        reference_df[['B', 'C', 'A']],
        reference_df[['D', 'E']]
    ])

    catalog.nb_rows = len(reference_df.index)

    # WHEN reads in first chunk
    await assert_fast_track(ctx_fixture, catalog, reference_df[['C', 'B', 'A']], columns=['C', 'B', 'A'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['A']], columns=['A'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['A']].iloc[1:3], columns=['A'], offset=1, limit=2)

    # WHEN reads in second chunk
    await assert_fast_track(ctx_fixture, catalog, reference_df[['E', 'D']], columns=['E', 'D'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['E']], columns=['E'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['D']].iloc[1:3], columns=['D'], offset=1, limit=2)

    # WHEN reads in both chunks
    await assert_fast_track(ctx_fixture, catalog, reference_df)
    await assert_fast_track(ctx_fixture, catalog, reference_df, columns=list(reference_df.columns))
    await assert_fast_track(ctx_fixture, catalog, reference_df[['E', 'A']], columns=['E', 'A'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['E', 'A']].iloc[1:3],
                            columns=['E', 'A'], offset=1, limit=2)


@pytest.mark.asyncio
async def test_shifted_multi_chunk_case(nope_logger_fixture, ctx_fixture, bulk_storage_mock):
    md_df = generate_df(['MD'], index=range(10))
    switched_gr_df = generate_df(['GR'], index=range(4, 10))
    switched_den_df = generate_df(['DEN'], index=range(6))
    index_df = pd.DataFrame(index=md_df.index)

    reference_df = pd.concat([index_df, md_df, switched_gr_df, switched_den_df], axis=1)

    catalog = await store_chunks(bulk_storage_mock, ctx_fixture.tenant, [
        md_df, switched_gr_df, switched_den_df
    ])

    # storage index and update catalog
    catalog.index_path = storage_path_builder.join('_wdms_index_', 'index.parquet')

    await bulk_storage_mock.upload(ctx_fixture.tenant,
                                   storage_path_builder.join(
                                       storage_path_builder.record_path('', catalog.record_id),
                                       catalog.index_path
                                   ),
                                   index_df.to_parquet(None, index=True))

    catalog.nb_rows = len(reference_df.index)

    # without offset/limit
    await assert_fast_track(ctx_fixture, catalog, reference_df[['MD']], columns=['MD'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['GR']], columns=['GR'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['DEN']], columns=['DEN'])
    await assert_fast_track(ctx_fixture, catalog, reference_df[['MD', 'DEN']], columns=['MD', 'DEN'])

    # with offset/limit
    await assert_fast_track(ctx_fixture, catalog, reference_df[['GR']].iloc[2:6], columns=['GR'], offset=2, limit=4)
    await assert_fast_track(ctx_fixture, catalog, reference_df[['DEN']].iloc[5:8], columns=['DEN'], offset=5, limit=3)
    await assert_fast_track(ctx_fixture, catalog, reference_df[['MD', 'GR']].iloc[5:], columns=['MD', 'GR'], offset=5)


call_count = 0


@pytest.mark.asyncio
async def test_load_dataframe_concurrency_is_limited(nope_logger_fixture, ctx_fixture):
    sync_event = asyncio.Event()
    data = pd.DataFrame().to_parquet(index=True)
    global call_count
    call_count = 0

    async def download_mock(*_, **__):
        global call_count
        call_count = call_count + 1
        await asyncio.wait_for(sync_event.wait(), 10)
        return data

    storage_mock = Mock()
    storage_mock.download = download_mock

    tasks = [asyncio.create_task(ft._load_dataframe_from_storage(storage_mock, Mock(), "")) for _ in range(250)]
    await asyncio.sleep(1)

    # only 100 download should been started
    assert call_count == 100

    # release them all
    sync_event.set()
    await asyncio.wait_for(asyncio.gather(*tasks), 10)

    # all completed
    assert call_count == 250
