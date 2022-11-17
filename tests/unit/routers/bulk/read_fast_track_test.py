import anyio

import uuid
from io import BytesIO

import pandas as pd

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from app.bulk_persistence import BulkCatalog, MimeTypes, MimeType, JSONOrient, BulkReadFilters, BulkFilter, \
    BulkReadFilterOperator, TooManyColumnsRequested
from app.bulk_persistence.dask import storage_path_builder
from app.bulk_persistence.dask.bulk_catalog import BulkCatalogOrigin, ChunkGroup
from app.bulk_persistence.dask.errors import TooManyValuesRequested
from app.bulk_persistence.dask.session_file_meta import generate_chunk_filename
from app.routers.bulk import read_fast_track

import pytest
from unittest.mock import AsyncMock, Mock
from pandas.testing import assert_frame_equal
from tests.unit.test_utils import ctx_fixture
from tests.unit.generate_data import generate_df
from tests.unit.blob_storage_fsspec import BlobStorageFsspec

format_params = [
    pytest.param(MimeTypes.PARQUET, None, id="parquet"),
    pytest.param(MimeTypes.JSON, JSONOrient.split, id="json")
]


def assert_dataframe_from_content(expected_df, content, accept_type, orient):
    if accept_type == MimeTypes.PARQUET:
        actual_df = pd.read_parquet(BytesIO(content))
    else:
        actual_df = pd.read_json(BytesIO(content), orient=orient.value)
    assert_frame_equal(expected_df, actual_df, check_dtype=accept_type == MimeTypes.PARQUET)
    # check_dtype to False as json may lose strict type


async def assert_fast_track(*, ctx, catalog, accept_type, orient,
                            expected_df,
                            offset=None, limit=None, columns=None):
    # WHEN read full bulk
    response = await read_fast_track.read_data_fast_track(ctx, catalog, accept_type, orient, BulkReadFilters([]),
                                                          offset=offset, limit=limit, curves_selection=columns)

    # THEN
    assert_dataframe_from_content(expected_df, response.body, accept_type, orient)


@pytest.mark.anyio
async def test_forward_parquet(nope_logger_fixture):
    storage_mock = Mock()
    storage_mock.download = AsyncMock(return_value=b'fake data')

    result = await read_fast_track._forward_parquet(storage_mock, Mock(), Mock())

    assert result.media_type == "application/x-parquet"
    assert result.body == b'fake data'


def test_split_dataframe_iloc(nope_logger_fixture):
    df = generate_df(['A'], index=range(10))

    assert_frame_equal(df, read_fast_track._split_dataframe_iloc(df))

    actual_df = read_fast_track._split_dataframe_iloc(df, offset=2)
    assert_frame_equal(df.iloc[2:], actual_df)
    # just double check
    assert actual_df.shape == (8, 1)
    assert actual_df.index[0] == 2

    actual_df = read_fast_track._split_dataframe_iloc(df, limit=5)
    assert_frame_equal(df.iloc[:5], actual_df)
    assert actual_df.shape == (5, 1)
    assert actual_df.index[0] == 0

    actual_df = read_fast_track._split_dataframe_iloc(df, offset=2, limit=5)
    assert_frame_equal(df.iloc[2:7], actual_df)
    assert actual_df.shape == (5, 1)
    assert actual_df.index[0] == 2


@pytest.mark.anyio
@pytest.mark.parametrize(["accept_type", "orient"], format_params)
async def test_build_response_df(nope_logger_fixture, accept_type: MimeType, orient):
    df = generate_df(['B', 'C', 'A'], index=range(6))

    result = await read_fast_track._build_response_from_df(df, accept_type, orient, requested_columns=['A', 'C'])
    assert accept_type.match(result.media_type)
    assert_dataframe_from_content(df[['A', 'C']], result.body, accept_type, orient)

    result = await read_fast_track._build_response_from_df(df, accept_type, orient)
    assert accept_type.match(result.media_type)
    assert_dataframe_from_content(df[['A', 'B', 'C']], result.body, accept_type, orient)  # column in natural order


@pytest.mark.anyio
@pytest.mark.parametrize(["accept_type", "orient"], format_params)
async def test_build_response_big_df(nope_logger_fixture, accept_type: MimeType, orient):
    df = generate_df(['B', 'C', 'A'], index=range(350_000))
    result = await read_fast_track._build_response_from_df(df, accept_type, orient)
    assert accept_type.match(result.media_type)
    assert_dataframe_from_content(df[['A', 'B', 'C']], result.body, accept_type, orient)


@pytest.mark.anyio
async def test_load_dataframe_from_storage(nope_logger_fixture):
    df = generate_df(['B', 'C', 'A'], index=range(6))

    storage_mock = Mock()
    storage_mock.download = AsyncMock(return_value=df.to_parquet(index=True))
    cmn_kwargs = {"storage": storage_mock, "tenant": Mock(), "obj_path": "mock", "total_columns_count": 3}
    actual_df = await read_fast_track._load_dataframe_from_storage(**cmn_kwargs)
    assert_frame_equal(df, actual_df)

    assert_frame_equal(
        df[['A', 'B']],
        await read_fast_track._load_dataframe_from_storage(**cmn_kwargs, columns_to_load=['A', 'B'])
    )

    assert_frame_equal(
        df.iloc[4:],
        await read_fast_track._load_dataframe_from_storage(**cmn_kwargs, offset=4)
    )

    assert_frame_equal(
        df.iloc[:3],
        await read_fast_track._load_dataframe_from_storage(**cmn_kwargs, limit=3)
    )

    assert_frame_equal(
        df.iloc[1: 4],
        await read_fast_track._load_dataframe_from_storage(**cmn_kwargs, offset=1, limit=3)
    )

    assert_frame_equal(
        df[['A', 'B']].iloc[1: 4],
        await read_fast_track._load_dataframe_from_storage(**cmn_kwargs, columns_to_load=['A', 'B'], offset=1, limit=3)
    )


@pytest.mark.anyio
async def test_load_dataframe_from_storage_many_columns(nope_logger_fixture):
    cols = [f'c{i}' for i in range(read_fast_track.MAX_COLUMNS_DIRECT_PARQUET + 10)]
    df = generate_df([f'c{i}' for i in range(read_fast_track.MAX_COLUMNS_DIRECT_PARQUET + 10)], index=range(10))
    storage_mock = Mock()
    storage_mock.download = AsyncMock(return_value=df.to_parquet(index=True))
    actual_df = await read_fast_track._load_dataframe_from_storage(storage_mock, Mock(), "mock", len(cols))
    assert_frame_equal(df, actual_df)

    cols_requested = cols[2:]
    actual_df = await read_fast_track._load_dataframe_from_storage(storage_mock, Mock(), "mock", len(cols), cols_requested)
    assert_frame_equal(df[cols_requested], actual_df)


@pytest.mark.anyio
async def test_unsupported_cases_raise(nope_logger_fixture):
    supported_filters = BulkReadFilters([])
    supported_format = MimeTypes.PARQUET

    # no filters
    with pytest.raises(read_fast_track.ReadFastTrackCaseNotSupportedException):
        await read_fast_track.read_data_fast_track(Mock(), BulkCatalog(''), supported_format, None,
                                                   BulkReadFilters(
                                                       [BulkFilter('MD', BulkReadFilterOperator.Greater, '10')]))

    # single file but save by multi partitions Dask, like conflict resolution on commit session
    with pytest.raises(read_fast_track.ReadFastTrackCaseNotSupportedException):
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
        await read_fast_track.read_data_fast_track(AsyncMock(), catalog, supported_format, None, supported_filters)

    # same as before but multi chunks
    with pytest.raises(read_fast_track.ReadFastTrackCaseNotSupportedException):
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.from_file())
        catalog.add_chunk(ChunkGroup({'A'}, ['path1'], ["Int32"]))
        catalog.add_chunk(ChunkGroup({'A', 'B'}, [f'{uuid.uuid4()}.parquet'], ["Int32"]))
        await read_fast_track.read_data_fast_track(AsyncMock(), catalog, supported_format, None, supported_filters,
                                                   curves_selection=['B'])

    # multi files, previous Dask storage (no catalog)
    with pytest.raises(read_fast_track.ReadFastTrackCaseNotSupportedException):
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
        catalog.add_chunk(ChunkGroup({'A', 'B'}, ["path1", "path2"], ["Int32"]))
        assert catalog.chunk_count > 1
        await read_fast_track.read_data_fast_track(AsyncMock(), catalog, supported_format, None, supported_filters)

    # chunks are not vertically slided - 1
    with pytest.raises(read_fast_track.ReadFastTrackCaseNotSupportedException):
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.from_file())
        catalog.add_chunk(ChunkGroup({'A'}, ['path1', 'paths2'], ["Int32"]))
        await read_fast_track.read_data_fast_track(AsyncMock(), catalog, supported_format, None, supported_filters)

    # chunks are not vertically slided - 2
    with pytest.raises(read_fast_track.ReadFastTrackCaseNotSupportedException):
        catalog = BulkCatalog('', origin=BulkCatalogOrigin.from_file())
        catalog.add_chunk(ChunkGroup({'A'}, ['path1'], ["Int32"]))
        catalog.add_chunk(ChunkGroup({'A', 'B'}, ['paths2'], ["Int32"]))
        await read_fast_track.read_data_fast_track(AsyncMock(), catalog, supported_format, None, supported_filters)


@pytest.mark.anyio
async def test_request_too_many_column_raise(nope_logger_fixture):
    catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
    catalog.add_chunk(ChunkGroup({f'C[{i}]' for i in range(5001)}, ["path1"], []))
    args = [AsyncMock(), catalog, MimeTypes.PARQUET, None, BulkReadFilters([])]

    # read all
    with pytest.raises(TooManyColumnsRequested) as ex_info:
        await read_fast_track.read_data_fast_track(*args, curves_selection=None)

    # read 3000+ columns
    curve_selection = [f'C[{i}]' for i in range(1000, 4001)]
    with pytest.raises(TooManyColumnsRequested):
        await read_fast_track.read_data_fast_track(*args, curves_selection=curve_selection)

    # read 3000+ columns even with limit
    with pytest.raises(TooManyColumnsRequested):
        await read_fast_track.read_data_fast_track(*args, curves_selection=curve_selection, offset=10, limit=1)


@pytest.mark.anyio
async def test_request_too_many_values_raise(nope_logger_fixture):
    catalog = BulkCatalog('', origin=BulkCatalogOrigin.generated_from_bulk())
    catalog.add_chunk(ChunkGroup({f'C[{i}]' for i in range(100)}, ["path1"], []))
    catalog.nb_rows = 1_000_000
    args = [AsyncMock(), catalog, MimeTypes.PARQUET, None, BulkReadFilters([])]

    # request 6M
    with pytest.raises(TooManyValuesRequested) as ex_info:
        await read_fast_track.read_data_fast_track(*args, curves_selection=[f'C[{i}]' for i in range(6)])

    # request 4M but need to work on a 100M dataframe
    with pytest.raises(TooManyValuesRequested) as ex_info:
        await read_fast_track.read_data_fast_track(*args, limit=40_000)


@pytest.fixture
async def bulk_storage_mock(ctx_fixture, tmp_path_factory):
    local_blob_path = str(tmp_path_factory.mktemp(basename="blob-"))
    blob_storage = BlobStorageFsspec(local_blob_path, 'file', auto_mkdir=True)

    async def _storage_mock(*_, **__):
        return blob_storage

    ctx_fixture.app_injector.register(BlobStorageBase, _storage_mock)
    return blob_storage

    ctx_fixture.app_injector.register(BlobStorageBase, AsyncMock())


async def store_chunks(storage: BlobStorageBase, tenant, chunks) -> BulkCatalog:
    catalog = BulkCatalog('r_id', origin=BulkCatalogOrigin.from_file())
    for df in chunks:
        chunk_filename = generate_chunk_filename(df) + '.parquet'
        chunk_path = storage_path_builder.join(storage_path_builder.record_path('', catalog.record_id), chunk_filename)
        catalog.add_chunk(ChunkGroup(set(df.columns), [chunk_filename], []))
        await storage.upload(tenant, chunk_path, df.to_parquet(None, index=True))
    return catalog


@pytest.mark.anyio
@pytest.mark.parametrize(["accept_type", "orient"], format_params)
async def test_single_chunk_case(nope_logger_fixture, ctx_fixture, bulk_storage_mock, accept_type, orient):
    # GIVEN single chunk stored
    reference_df = generate_df(['A', 'B', 'C'], index=range(6))
    catalog = await store_chunks(bulk_storage_mock, ctx_fixture.tenant, [reference_df])
    catalog.nb_rows = len(reference_df.index)
    common_kwargs = {"ctx": ctx_fixture, "catalog": catalog, "accept_type": accept_type, "orient": orient}

    # WHEN read full bulk
    await assert_fast_track(**common_kwargs, expected_df=reference_df)
    await assert_fast_track(**common_kwargs, expected_df=reference_df, columns=['A', 'B', 'C'])

    # WHEN read all columns, ensure column order
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['B', 'A']], columns=['B', 'A'])

    # WHEN read one column
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['A']], columns=['A'])

    # WHEN read few columns, offset, limit
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['A']].iloc[1:3], columns=['A'], offset=1,
                            limit=2)

    # WHEN offset is negative
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['A']], columns=['A'], offset=-1)

    # WHEN limit exceed row count
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['A']], columns=['A'], limit=1_000)
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['A']].iloc[1:], columns=['A'], offset=1,
                            limit=1_000)


@pytest.mark.anyio
@pytest.mark.parametrize(["accept_type", "orient"], format_params)
async def test_single_chunk_case_many_columns(nope_logger_fixture, ctx_fixture, bulk_storage_mock, accept_type, orient):
    cols = [f'c{i}' for i in range(510)]
    reference_df = generate_df(cols, index=range(6))
    catalog = await store_chunks(bulk_storage_mock, ctx_fixture.tenant, [reference_df])
    catalog.nb_rows = len(reference_df.index)
    common_kwargs = {"ctx": ctx_fixture, "catalog": catalog, "accept_type": accept_type, "orient": orient}

    # WHEN read full bulk
    await assert_fast_track(**common_kwargs, expected_df=reference_df)
    await assert_fast_track(**common_kwargs, expected_df=reference_df, columns=cols)
    await assert_fast_track(**common_kwargs, expected_df=reference_df[cols[2:]], columns=cols[2:])


@pytest.mark.anyio
@pytest.mark.parametrize(["accept_type", "orient"], format_params)
async def test_multi_chunk_case(nope_logger_fixture, ctx_fixture, bulk_storage_mock, accept_type, orient):
    # GIVEN df split into 2 chunks
    reference_df = generate_df(['A', 'B', 'C', 'D', 'E'], index=range(6))
    catalog = await store_chunks(bulk_storage_mock, ctx_fixture.tenant, [
        reference_df[['B', 'C', 'A']],
        reference_df[['D', 'E']]
    ])

    catalog.nb_rows = len(reference_df.index)
    common_kwargs = {"ctx": ctx_fixture, "catalog": catalog, "accept_type": accept_type, "orient": orient}

    # WHEN reads in first chunk
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['C', 'B', 'A']], columns=['C', 'B', 'A'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['A']], columns=['A'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['A']].iloc[1:3],
                            columns=['A'], offset=1, limit=2)

    # WHEN reads in second chunk
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['E', 'D']], columns=['E', 'D'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['E']], columns=['E'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['D']].iloc[1:3],
                            columns=['D'], offset=1, limit=2)

    # WHEN reads in both chunks
    await assert_fast_track(**common_kwargs, expected_df=reference_df)
    await assert_fast_track(**common_kwargs, expected_df=reference_df, columns=list(reference_df.columns))
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['E', 'A']], columns=['E', 'A'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['E', 'A']].iloc[1:3],
                            columns=['E', 'A'], offset=1, limit=2)

    # WHEN offset is negative
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['E', 'A']], columns=['E', 'A'], offset=-1)

    # WHEN limit exceed row count
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['E', 'A']], columns=['E', 'A'], limit=1_000)
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['E', 'A']].iloc[1:], columns=['E', 'A'],
                            offset=1, limit=1_000)


@pytest.mark.anyio
@pytest.mark.parametrize(["accept_type", "orient"], format_params)
async def test_multi_chunk_case_many_columns(nope_logger_fixture, ctx_fixture, bulk_storage_mock, accept_type, orient):
    cols = [f'c{i}' for i in range(600)]
    reference_df = generate_df(cols, index=range(6))
    catalog = await store_chunks(bulk_storage_mock, ctx_fixture.tenant, [
        reference_df[cols[:300]],
        reference_df[cols[300:]]
    ])
    catalog.nb_rows = len(reference_df.index)
    common_kwargs = {"ctx": ctx_fixture, "catalog": catalog, "accept_type": accept_type, "orient": orient}

    # WHEN read full bulk
    await assert_fast_track(**common_kwargs, expected_df=reference_df)
    await assert_fast_track(**common_kwargs, expected_df=reference_df, columns=cols)
    await assert_fast_track(**common_kwargs, expected_df=reference_df[cols[2:]], columns=cols[2:])


@pytest.mark.anyio
@pytest.mark.parametrize(["accept_type", "orient"], format_params)
async def test_shifted_multi_chunk_case(nope_logger_fixture, ctx_fixture, bulk_storage_mock, accept_type, orient):
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
    common_kwargs = {"ctx": ctx_fixture, "catalog": catalog, "accept_type": accept_type, "orient": orient}

    # without offset/limit
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['MD']], columns=['MD'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['GR']], columns=['GR'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['DEN']], columns=['DEN'])
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['MD', 'DEN']], columns=['MD', 'DEN'])

    # with offset/limit
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['GR']].iloc[2:6],
                            columns=['GR'], offset=2, limit=4)
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['DEN']].iloc[5:8],
                            columns=['DEN'], offset=5, limit=3)
    await assert_fast_track(**common_kwargs, expected_df=reference_df[['MD', 'GR']].iloc[5:],
                            columns=['MD', 'GR'], offset=5)


call_count = 0




@pytest.mark.anyio
async def test_load_dataframe_concurrency_is_limited(nope_logger_fixture, ctx_fixture, anyio_backend):

    data = pd.DataFrame().to_parquet(index=True)
    global call_count
    call_count = 0

    async with anyio.create_task_group() as tg:
        sync_event = anyio.Event()

        async def download_mock(*_, **__):
            global call_count
            call_count = call_count + 1
            await sync_event.wait()
            return data

        storage_mock = AsyncMock()
        storage_mock.download = download_mock

        for _ in range(250):
            tg.start_soon(read_fast_track._load_dataframe_from_storage, storage_mock, Mock(), "", 1)

        await anyio.sleep(1)
        # only 100 download should been started
        assert call_count == 100

        # release them all
        sync_event.set()


    # all completed
    assert call_count == 250
