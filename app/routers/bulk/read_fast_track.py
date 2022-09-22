from typing import Optional
import asyncio
from io import BytesIO

import pandas as pd

from fastapi import Response

from osdu.core.api.storage.blob_storage_base import BlobStorageBase

from app.bulk_persistence.dask.errors import TooManyValuesRequested
from app.helper.logger import get_logger
from app.helper.traces import with_trace

from app.bulk_persistence import (BulkCatalog,
                                  MimeType, MimeTypes, JSONOrient,
                                  BulkCurvesNotFound,
                                  BulkReadFilters,
                                  DataframeSerializerSync, DataframeSerializerAsync, TooManyColumnsRequested)
from app.bulk_persistence.capture_timings import capture_timings, timeit
from app.bulk_persistence.dask import storage_path_builder
from app.bulk_persistence.dataframe_columns import ColumnSelection, select_columns, sort_dataframe_column

"""
    The purpose of read fast track to speed up read on some specific circumstances
"""


class ReadFastTrackCaseNotSupportedException(Exception):
    """ Fast track cannot be applied """
    pass


MAX_COLUMNS_COUNT = 3_000  # restrict to max 3 000 columns
MAX_TOTAL_VALUES_COUNT_FILTERED = 5_000_000  # restrict to max 5M values at once (~50MB in parquet)
MAX_TOTAL_VALUES_COUNT_UNFILTERED = 20_000_000  # restrict to max 20M values at once (~200MB in parquet)
LOAD_DATAFRAME_SEMAPHORE = asyncio.Semaphore(100)  # semaphore to not overwhelm the service


@with_trace('get_data_fast_track')
@capture_timings('get_data_fast_track')
async def read_data_fast_track(ctx,
                               bulk_catalog: BulkCatalog,
                               accept_type: MimeType,
                               orient: Optional[JSONOrient],
                               bulk_filters: BulkReadFilters,
                               offset: Optional[int] = None,
                               limit: Optional[int] = None,
                               curves_selection: Optional[ColumnSelection] = None) -> Response:
    """
        attempt a fast track read on some circumstances, for now:
            - parquet format only
            - no filter
            - chunk should be broken down perfectly column wise, each column is inside one and only one chunk (chunk
            may contains several columns)
        in any other cases, it raises ReadFastTrackCaseNotSupportedException
         :param ctx: context
         :param bulk_catalog: bulk catalog
         :param accept_type: out mime format
         :param orient: out mime format
         :param bulk_filters: out mime format
         :param offset: offset
         :param limit: limit
         :param curves_selection: curves_selection, note: slice notation must be resolved before
         :return: Response
    """
    # ---------- first check if fast track can be applied -----------------------------
    if bulk_filters.has_filter():
        # cases not supported yet
        raise ReadFastTrackCaseNotSupportedException()

    # for now short if no filtering at all and parquet
    columns_to_load = bulk_catalog.all_columns

    # get the actual column to fetch from the given curve selection
    if curves_selection is not None:
        columns_to_load, curves_non_existent = select_columns(curves_selection, columns_to_load)
        if curves_non_existent:
            raise BulkCurvesNotFound(curves=curves_non_existent)

    # validate the column count requested
    if len(columns_to_load) > MAX_COLUMNS_COUNT:
        raise TooManyColumnsRequested(len(columns_to_load), MAX_COLUMNS_COUNT)

    # validate the values count before any filtering
    total_values_unfiltered = bulk_catalog.nb_rows * len(columns_to_load)
    if total_values_unfiltered > MAX_TOTAL_VALUES_COUNT_UNFILTERED:
        raise TooManyValuesRequested(total_values_unfiltered, MAX_TOTAL_VALUES_COUNT_UNFILTERED)

    # validate the values after filtering
    filtered_row_count = bulk_catalog.nb_rows
    if offset:
        filtered_row_count = max(0, filtered_row_count - offset)
    if limit:
        if limit >= filtered_row_count:
            limit = None  # so further algo could run like there's no limit
        else:
            filtered_row_count = limit
    total_values_filtered = filtered_row_count * len(columns_to_load)

    if total_values_filtered > MAX_TOTAL_VALUES_COUNT_FILTERED:
        raise TooManyValuesRequested(total_values_filtered, MAX_TOTAL_VALUES_COUNT_FILTERED)

    # ---------- first check if fast track can be applied -----------------------------
    storage = await ctx.app_injector.get(BlobStorageBase)
    base_chunk_path = storage_path_builder.record_path('', bulk_catalog.record_id)

    # ---------- case of single chunk -----------------------------
    # TODO try to use direct forward in case requested columns == single chunk all columns

    if bulk_catalog.chunk_count == 1:  # only one chunk
        for chunk_path in bulk_catalog.get_chunk_paths():
            if not bulk_catalog.is_single_file_chunk(chunk_path):
                # multi partition file chunk saved by Dask likely from a previous storage version
                # (todo check if this happen currently in case of conflict)
                raise ReadFastTrackCaseNotSupportedException()

            # return directly as there's one chunk
            return await _build_response_from_single_chunk(
                storage, ctx.tenant,
                storage_path_builder.join(base_chunk_path, chunk_path),
                accept_type, orient,
                None if curves_selection is None else columns_to_load,
                offset, limit)

    # more cases not supported
    if bulk_catalog.origin.was_generated:
        # previous storage mechanism with Dask partitions, the only case supported for a generated catalog is
        # a post data without session
        raise ReadFastTrackCaseNotSupportedException()

    # cases where involved chunks are not perfectly column-slided - 1 column = one chunk only
    if not bulk_catalog.is_columns_slide_only(None if curves_selection is None else columns_to_load):
        raise ReadFastTrackCaseNotSupportedException()

    # ---------- case of several chunks -----------------------------
    # for now should be perfectly column-slided - 1 column inside one chunk only

    # figures out the number of chunks involved, only one path each
    with timeit("bulk_catalog.filter_group_for_columns"):
        chunk_groups = bulk_catalog.filter_group_for_columns(columns_to_load)

    if any(len(chunk_group.paths) > 1 for chunk_group in chunk_groups):
        raise RuntimeError("unique chunk path expected")  # extra check is_columns_slide_only

    if any(not bulk_catalog.is_single_file_chunk(chunk_group.paths[0]) for chunk_group in chunk_groups):
        # at least one chunk is a multi partition file saved by Dask
        raise ReadFastTrackCaseNotSupportedException()

    # not putting offset, limit here because each chunk may not cover the full bulk index
    # by the way it might be possible to do something before concat
    load_chunk_df_coros = [
        _load_dataframe_from_storage(
            storage, ctx.tenant,
            storage_path_builder.join(base_chunk_path, chunk_group.paths[0]),
            chunk_group.labels.intersection(columns_to_load)
        ) for chunk_group in chunk_groups
    ]
    load_index_df_coro = _read_index(storage, ctx.tenant, bulk_catalog)

    with timeit(f"load {len(chunk_groups)} chunk dataframes and index dataframes"):
        dfs = await asyncio.gather(
            load_index_df_coro,  # index dataframe
            *load_chunk_df_coros  # chunks
        )

    # concat df + select rows if needed
    with timeit(f"concat and potentially cut {len(dfs)} dataframes"):
        final_df = pd.concat(dfs, axis=1)
        final_df = _split_dataframe_iloc(final_df, offset, limit)

    # build the final response by serializing the dataframe into requested format
    return await _build_response_from_df(
        final_df,
        accept_type, orient,
        requested_columns=None if curves_selection is None else columns_to_load
    )


async def _build_response_to_parquet(df: pd.DataFrame) -> Response:
    row_count, col_count = df.shape

    # decide to compute in main or in executor, based on column count and total values
    direct = col_count < 500 and (row_count * col_count) < 1_000_000

    with timeit(f"to parquet dataframe of shape {df.shape}, direct {direct}"):
        if direct:
            content = DataframeSerializerSync().to_parquet(df)
        else:
            content = await DataframeSerializerAsync().to_parquet(df)
    return Response(content, media_type=MimeTypes.PARQUET.type)


async def _build_response_to_json(df: pd.DataFrame, orient: JSONOrient) -> Response:
    row_count, col_count = df.shape

    # decide to compute in main or in executor, based on column count and total values
    direct = col_count < 500 and (row_count * col_count) < 1_000_000

    with timeit(f"to json dataframe of shape {df.shape}, direct {direct}"):
        if direct:
            content = DataframeSerializerSync().to_json(df, orient)
        else:
            content = await DataframeSerializerAsync().to_json(df, orient)
    return Response(content, media_type=MimeTypes.JSON.type)


@capture_timings('_build_response_from_df')
async def _build_response_from_df(df: pd.DataFrame,
                                  accept_type: MimeType,
                                  orient: Optional[JSONOrient],
                                  requested_columns=None) -> Response:
    """ serialize the dataframe into parquet and construct the http response """

    # column ordering similar to utils.process_params
    if requested_columns:
        df = df[requested_columns]  # columns are ordered as the user requested
    else:
        with timeit("sort_dataframe_columns"):
            df = sort_dataframe_column(df)  # columns are ordered by natural sort

    df.index.name = None  # similar to 'df_render'
    if accept_type == MimeTypes.PARQUET:
        return await _build_response_to_parquet(df)

    if accept_type == MimeTypes.JSON:
        return await _build_response_to_json(df, orient)

    raise RuntimeError(f"unsupported format {accept_type}")


def _split_dataframe_iloc(df: pd.DataFrame, offset: Optional[int] = None, limit: Optional[int] = None) -> pd.DataFrame:
    """ select range  """
    if offset and limit:
        return df.iloc[offset:offset + limit]
    if offset:
        return df.iloc[offset:]
    if limit:
        return df.iloc[:limit]
    return df


@with_trace('_load_dataframe_from_storage')
@capture_timings('_load_dataframe_from_storage')
async def _load_dataframe_from_storage(storage: BlobStorageBase,
                                       tenant,
                                       obj_path: str,
                                       columns=None,
                                       offset: Optional[int] = None,
                                       limit: Optional[int] = None) -> pd.DataFrame:
    # limit the concurrency to not overwhelm the service
    async with LOAD_DATAFRAME_SEMAPHORE:
        content = await storage.download(tenant, obj_path)
        df = pd.read_parquet(BytesIO(content), columns=columns)
        return _split_dataframe_iloc(df, offset, limit)


@with_trace('_read_index')
@capture_timings('_read_index')
async def _read_index(storage: BlobStorageBase, tenant, bulk_catalog: BulkCatalog) -> pd.DataFrame:
    if not bulk_catalog.index_path:
        get_logger().warning(f"not index file for record {bulk_catalog.record_id}")
        return pd.DataFrame()

    index_path = storage_path_builder.full_path('', bulk_catalog.record_id, bulk_catalog.index_path)
    return await _load_dataframe_from_storage(storage, tenant, index_path)


async def _build_response_from_single_chunk(storage: BlobStorageBase,
                                            tenant,
                                            blob_path,
                                            accept_type: MimeType,
                                            orient: Optional[JSONOrient],
                                            requested_columns=None,
                                            offset: Optional[int] = None,
                                            limit: Optional[int] = None) -> Response:
    # only one chunk
    if requested_columns or offset or limit or accept_type == MimeTypes.JSON:
        df = await _load_dataframe_from_storage(storage, tenant, blob_path, requested_columns, offset, limit)
        return await _build_response_from_df(df, accept_type, orient, requested_columns=requested_columns)
    else:
        # easy fast track, just forward it
        return await _forward_parquet(storage, tenant, blob_path)


@with_trace('_forward_parquet')
@capture_timings('_forward_parquet')
async def _forward_parquet(storage: BlobStorageBase, tenant, parquet_path) -> Response:
    content = await storage.download(tenant, parquet_path)

    # simply forward content as-it
    return Response(content, media_type=MimeTypes.PARQUET.type)
