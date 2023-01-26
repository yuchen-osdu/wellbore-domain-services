from contextlib import suppress
from typing import Optional
from fastapi import Response
import pandas as pd

from .read_fast_track import ReadFastTrackCaseNotSupportedException, read_data_fast_track
from .model_chunking import GetDataParams
from .mime_types import MimeType, MimeTypes
from .json_orient import JSONOrient
from .bulk_uri import BulkURI
from .bulk_filter import BulkReadFilters
from .bulk_persistence_config import MAX_COLUMNS_RETURN
from .dataframe_validators import auto_cast_columns_to_string
from .dataframe_persistence import get_dataframe

from .dask.bulk_catalog import BulkCatalog
from .dask.dataframe_render import DataFrameRender
from .dask.errors import FilterError, TooManyColumnsRequested
from .dask.dask_bulk_storage import DaskBulkStorage

from app.helper.traces import with_trace


def _build_describe_response(describe):
    """ for performance reason in case of many columns """
    columns = str(describe.columns).replace("'", '"')
    json_string = f"{'{'}\"numberOfRows\":{describe.numberOfRows}, \"columns\":{columns}{'}'}"
    return Response(
        content=json_string,
        media_type=MimeTypes.JSON.type
    )


@with_trace('_process_request_v1')
async def _process_request_v1(record_id: str,
                              bulk_id: str,
                              data_param: GetDataParams,
                              filters: BulkReadFilters,
                              bulk_catalog: BulkCatalog,
                              dask_blob_storage: DaskBulkStorage):
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
            raise FilterError(f'The columns:{list(invalid_columns)} to be filtered do not exist')
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


class BulkReaderDask:
    def __init__(self, fast_track: bool):
        self._fast_track = fast_track

    @with_trace("dask.read_data")
    async def read_data(self,
                        ctx,
                        record_id: str,
                        bulk_uri: BulkURI,
                        data_param: GetDataParams,
                        accept_type: MimeType,
                        orient: Optional[JSONOrient]) -> Response:
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
                    offset=data_param.offset,
                    limit=data_param.limit,
                    column_selection=column_selection)
                return _build_describe_response(descr)

            # if fast track enabled, try it
            if self._fast_track:
                with suppress(ReadFastTrackCaseNotSupportedException):
                    return await read_data_fast_track(ctx, bulk_catalog,
                                                      accept_type, orient,
                                                      bulk_filters,
                                                      data_param.offset,
                                                      data_param.limit,
                                                      column_selection)

            df, filters, columns = await _process_request_v1(record_id,
                                                             bulk_id,
                                                             data_param,
                                                             bulk_filters,
                                                             bulk_catalog,
                                                             dask_blob_storage)

            if data_param.offset or data_param.limit:
                future_index = await dask_blob_storage.load_index(record_id, bulk_id, bulk_catalog)

        df = await DataFrameRender.process_params(df, data_param, bulk_filters, dask_blob_storage, future_index)

        return await DataFrameRender.df_render(df,
                                               dask_blob_storage,
                                               data_param,
                                               accept_type,
                                               orient=orient,
                                               columns=columns)
