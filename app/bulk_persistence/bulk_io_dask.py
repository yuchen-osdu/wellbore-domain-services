from contextlib import suppress
from uuid import UUID
from typing import Optional, Union, AsyncGenerator, Tuple, List

import pandas as pd
from fastapi import Response
from fastapi.encoders import jsonable_encoder

from odes_storage.models import Record
from starlette.responses import JSONResponse
from osdu.core.api.storage.exceptions import ResourceNotFoundException

from .statistics.bulk_statistics import BulkStatistics
from .statistics.models import BulkDataStatisticsResponse
from .read_fast_track import ReadFastTrackCaseNotSupportedException, read_data_fast_track
from .model_chunking import GetDataParams
from .mime_types import MimeType, MimeTypes
from .json_orient import JSONOrient
from .bulk_uri import BulkURI
from .bulk_filter import BulkReadFilters
from .bulk_persistence_config import MAX_COLUMNS_RETURN
from .dataframe_validators import auto_cast_columns_to_string, no_validation
from .dataframe_persistence import get_dataframe, download_bulk
from .bulk_io import BulkIO
from .dataframe_validators import DataFrameValidationFunc
from .consistency_checks import DataConsistencyChecks, BulkInfoForConsistency
from .sessions_storage import Session

from .dask.bulk_catalog import BulkCatalog
from .dask.dataframe_render import DataFrameRender
from .dask.errors import FilterError, TooManyColumnsRequested, BulkRecordNotFound
from .dask.dask_bulk_storage import DaskBulkStorage

from app.helper.traces import with_trace


def _build_describe_response(describe):
    """for performance reason in case of many columns"""
    columns = str(describe.columns).replace("'", '"')
    json_string = f"{'{'}\"numberOfRows\":{describe.numberOfRows}, \"columns\":{columns}{'}'}"
    return Response(content=json_string, media_type=MimeTypes.JSON.type)


@with_trace("_process_request_v1")
async def _process_request_v1(
        record_id: str,
        bulk_id: str,
        data_param: GetDataParams,
        filters: BulkReadFilters,
        bulk_catalog: BulkCatalog,
        dask_blob_storage: DaskBulkStorage,
):
    columns_to_load = None
    columns = bulk_catalog.all_columns
    existing_col = columns
    if data_param.curves:
        columns_to_load = DataFrameRender.get_matching_columns(data_param.get_curves_list(), existing_col)
        columns = set(columns_to_load)

    if not data_param.describe:  # don't limit columns when describe parameter is True
        # if curves parameter is None, it means that we are going to load all existing columns
        nb_cols_to_return = len(columns_to_load) if columns_to_load else len(existing_col)
        if nb_cols_to_return > MAX_COLUMNS_RETURN:
            raise TooManyColumnsRequested(nb_cols_to_return, MAX_COLUMNS_RETURN)

    if filters.has_filter():
        # get column needed for filtering which are not yet in columns
        invalid_columns = filters.columns - existing_col
        if invalid_columns:
            raise FilterError(f"The columns:{list(invalid_columns)} to be filtered do not exist")
        if columns_to_load:
            columns_to_load = filters.columns.union(columns_to_load)

    if columns_to_load is None and data_param.describe:
        # optimization: create a fake dataset when describe on all columns
        index = await dask_blob_storage.load_index(record_id, bulk_id, bulk_catalog)
        df = pd.DataFrame(index=index)
    else:
        # loading the dataframe with filter on columns is faster than filtering columns on df
        df = await dask_blob_storage.load_bulk(record_id, bulk_id, bulk_catalog, columns=columns_to_load)
    return df, filters, columns


class BulkIODask(BulkIO):
    """implementation of bulk I/O using Dask"""

    def __init__(self, fast_track: bool):
        self._fast_track = fast_track

    @with_trace("dask.read_data")
    async def read_data(
            self,
            ctx,
            record_id: str,
            bulk_uri: BulkURI,
            data_param: GetDataParams,
            accept_type: MimeType,
            orient: Optional[JSONOrient],
    ) -> Response:
        columns = None
        bulk_id = bulk_uri.bulk_id
        bulk_filters = BulkReadFilters(data_param.get_bulk_filters())
        dask_blob_storage: DaskBulkStorage = await ctx.app_injector.get(DaskBulkStorage)

        future_index = None
        if bulk_uri.is_bulk_storage_V0():
            df = await get_dataframe(ctx, bulk_id)
            auto_cast_columns_to_string(df)
        else:
            # in any case we need the catalog in any code path, because either 'read_stat' (to get the columns)
            # or 'load_index' will need it
            # TODO seems get columns/stat is not always needed - see df_render
            bulk_catalog = await dask_blob_storage.get_bulk_catalog(record_id, bulk_id)

            # if describe without filters, the catalog is enough to answer:
            column_selection = data_param.get_curves_list() if data_param.curves else None
            if data_param.describe and not bulk_filters.has_filter():
                descr = bulk_catalog.describe(
                    offset=data_param.offset, limit=data_param.limit, column_selection=column_selection
                )
                return _build_describe_response(descr)

            # if fast track enabled, try it
            if self._fast_track:
                with suppress(ReadFastTrackCaseNotSupportedException):
                    return await read_data_fast_track(
                        ctx,
                        bulk_catalog,
                        accept_type,
                        orient,
                        bulk_filters,
                        data_param.offset,
                        data_param.limit,
                        column_selection,
                    )

            df, filters, columns = await _process_request_v1(
                record_id, bulk_id, data_param, bulk_filters, bulk_catalog, dask_blob_storage
            )

            if data_param.offset or data_param.limit:
                future_index = await dask_blob_storage.load_index(record_id, bulk_id, bulk_catalog)

        df = await DataFrameRender.process_params(df, data_param, bulk_filters, dask_blob_storage, future_index)

        return await DataFrameRender.df_render(
            df, dask_blob_storage, data_param, accept_type, orient=orient, columns=columns
        )

    async def write_bulk(
            self,
            ctx,
            data: Union[bytes, AsyncGenerator[bytes, None]],
            content_type: MimeType,
            df_validator_func: DataFrameValidationFunc,
            consistency_checks: DataConsistencyChecks,
            record: Record,
    ) -> Tuple[str, BulkInfoForConsistency]:
        dask_blob_storage: DaskBulkStorage = await ctx.app_injector.get(DaskBulkStorage)
        return await dask_blob_storage.post_data_without_session(
            data=data,
            content_type=content_type,
            df_validator_func=df_validator_func,
            consistency_checks=consistency_checks,
            record=record,
        )

    async def write_chunk(
            self,
            ctx,
            data: Union[bytes, AsyncGenerator[bytes, None]],
            content_type: MimeType,
            df_validator_func: DataFrameValidationFunc,
            record_id: str,
            session_id: UUID,
    ) -> BulkInfoForConsistency:
        dask_blob_storage: DaskBulkStorage = await ctx.app_injector.get(DaskBulkStorage)

        # TODO for now return type does not match the return type hint, this will be fixed soon
        return await dask_blob_storage.add_chunk_in_session(
            data, content_type, df_validator_func, record_id, session_id
        )

    async def write_complete_session(
            self,
            ctx,
            record: Record,
            session: Session,
            update_from_bulk_uri: Optional[BulkURI],
            consistency_checks: DataConsistencyChecks,
    ) -> str:
        dask_blob_storage: DaskBulkStorage = await ctx.app_injector.get(DaskBulkStorage)
        previous_bulk_id = None
        if update_from_bulk_uri is not None:
            if update_from_bulk_uri.is_bulk_storage_V0():
                try:
                    data, content_type = await download_bulk(ctx, update_from_bulk_uri.bulk_id)
                    # convert old bulk to new one
                    previous_bulk_id, _ = await dask_blob_storage.post_data_without_session(
                        data=data,
                        content_type=content_type,
                        df_validator_func=no_validation,
                        consistency_checks=consistency_checks,
                        record=record,
                    )
                except ResourceNotFoundException:
                    BulkRecordNotFound(record_id=record.id, bulk_id=previous_bulk_id).raise_as_http()

            else:
                previous_bulk_id = update_from_bulk_uri.bulk_id

        new_bulk_id = await dask_blob_storage.session_commit(session, previous_bulk_id)

        await consistency_checks.check_bulk_consistency_on_commit_session(record, new_bulk_id)
        return new_bulk_id

    @with_trace("dask-get_statistics")
    async def get_statistics(
            self,
            ctx,
            record_id: str,
            bulk_uri: str,
            curves_selection: List[str],
    ) -> Response:
        dask_blob_storage: DaskBulkStorage = await ctx.app_injector.get(DaskBulkStorage)
        catalog = await dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        columns = DataFrameRender.get_matching_columns(curves_selection, catalog.all_columns)

        stats_df, stats_meta = await BulkStatistics(dask_blob_storage).get_bulk_statistics(catalog, record_id,
                                                                                           bulk_uri, columns)
        # replace np.nan by string "NaN" to have unified str type values for std column
        if not stats_df.empty:
            stats_df['std'].fillna(value=str("NaN"), inplace=True)

        # only orient: 'index' or 'columns' cam be read with pd.DataFrame.from_dict().
        result = BulkDataStatisticsResponse(**stats_meta.dict(by_alias=True), data=stats_df.to_dict(orient='index'))
        return JSONResponse(content=jsonable_encoder(result))

    @with_trace("dask-post_statistics")
    async def post_statistics(
        self,
        ctx,
        record_id: str,
        bulk_uri: str,
        record_version: int,
    ) -> Response:
        """
        Get data from a given record
        :param ctx: context instance
        :param record_id: record id as string
        :param bulk_uri: bulk uri as string
        :param record_version version of given record
        :return: Return bulk statistics if exist
        """
        dask_blob_storage: DaskBulkStorage = await ctx.app_injector.get(DaskBulkStorage)

        await BulkStatistics(dask_blob_storage).compute_bulk_statistics(record_id, bulk_uri, record_version)
