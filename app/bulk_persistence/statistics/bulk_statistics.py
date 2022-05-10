import asyncio
import functools
from typing import List, Callable, Iterable
import itertools
from datetime import datetime
from os.path import join
import numpy as np
import pandas as pd

from app.conf import Config
from app.helper.logger import get_logger
from .models import StatisticsComputationMeta, BulkStatisticsStatus

from .. import DataframeSerializerSync
from ..dask.traces import submit_with_trace
from ..dask.bulk_catalog import BulkCatalog
from ..dask.dask_bulk_storage import DaskBulkStorage, DASK_BACKGROUND_TASK_PRIORITY
from ..dask import storage_path_builder as path_builder
from .exceptions import (
    ComputationRunningError,
    RequestedCurvesError,
    StatisticsNotFoundError,
    ComputationNotCompleteError)

from osdu.core.api.storage import exceptions as osdu_storage_exception


def grouper(n, container: Iterable):
    """
    Return generator over a sub-list of 'n' elements of the given 'container'
    >>> list(grouper(4,['A', 'B', 'C', 'D', 'E', 'F']))
    returns: [('A', 'B', 'C', 'D'), ('E', 'F')]
    """
    n = int(n)
    it = iter(container)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def get_columns_count(max_number_values: int, max_columns_count: int, nb_rows: int, nb_cols: int) -> int:
    """
    Return the numbers of columns to be read at once in parquet files to stay under a given limit of maximum values.

    @param max_number_values: maximum number of values to be read at once, within several bulk files
    @param max_columns_count: maximum number of columns to be read whenever the limit is reached
    @param nb_rows: number of rows per bulk files (which must have the same shape)
    @param nb_cols: number of columns per bulk files (which must have the same shape)

        >>> get_columns_count(max_number_values=100_000, max_columns_count=500, nb_rows=10_000, nb_cols=10)
        >>> 10

        >>>> get_columns_count(max_number_values=100_000, max_columns_count=100, nb_rows=100_000, nb_cols=10)
        >>> 1
    """

    total_nb_values = nb_rows * nb_cols
    block_count = max(total_nb_values / max_number_values, 1)
    wanted_nb_col = max(int(nb_cols / block_count), 1)
    return min(max_columns_count, wanted_nb_col)


class BulkStatistics:

    # maximum number of bulk values to be fetched and computed per batch
    _paging_size_per_batch: int = 10_000_000
    # maximum number of columns of data to be fetched per batch of bulk files
    _max_cols_per_batch: int = Config.max_columns_return.value

    _stats_api_version = "1"
    _valid_values_label = 'total_count'
    _renaming_stats_labels = {'count': 'non_absent_values_count'}
    _percentiles = [.10, .5, .90]

    def __init__(self, dask_blob_storage: DaskBulkStorage):
        self.dask_blob_storage = dask_blob_storage

    def _submit_with_trace(self, target_func: Callable, *args, **kwargs):
        """ Enable tracing of given target_func run into Dask """
        return submit_with_trace(self.dask_blob_storage.client, target_func, *args, **kwargs)

    def _record_path(self, record_id: str):
        """
        Return the path to bulk data for record identified by the given record_id.
        """
        return path_builder.record_path(self.dask_blob_storage.base_directory,
                                        record_id,
                                        self.dask_blob_storage.protocol)

    def _statistics_base_path(self, record_id: str, bulk_id: str):
        """ Return the base path for bulk data statistics for current version """

        suffix = f'statistics.v{self._stats_api_version}'
        return path_builder.record_statistics_base_path(self.dask_blob_storage.base_directory,
                                                        record_id,
                                                        bulk_id,
                                                        suffix,
                                                        self.dask_blob_storage.protocol)

    def _statistics_data_path(self, record_id: str, bulk_id):
        """ Return the path for where statistics files are saved for a given record and bulk id """
        return join(self._statistics_base_path(record_id, bulk_id), 'data')

    def _fetch_bulk_batch(self, catalog: BulkCatalog, columns: List[str]) -> pd.DataFrame:
        """
            Read requested columns over bulk data parquet files and return it into one DataFrame.

            Data to be fetched can be in several files that possibly contains other unwanted columns.
            Requested Columns are fetched in each file provided by the bulk_catalog
             and then concatenate into one pd.DataFrame.
        """
        record_path = self._record_path(catalog.record_id)
        column_paths = catalog.get_paths_for_columns(columns, record_path)

        def read_parquets_same_schema(_col_path):
            _columns, _files_to_load = _col_path.labels, _col_path.paths

            _dfs = (pd.read_parquet(file, columns=_columns,
                                    storage_options=self.dask_blob_storage._parameters.storage_options)
                    for file in _files_to_load)
            return pd.concat(_dfs, ignore_index=True)

        dfs = (read_parquets_same_schema(col_path) for col_path in column_paths)
        return pd.concat(dfs, ignore_index=True)

    @staticmethod
    def _compute_statistics_batch(bulk_df: pd.DataFrame, catalog) -> pd.DataFrame:
        """
            Perform statistics computation on given piece of bulk data
            Note: Column 'std' (standard deviation) can be missing from results, when bulk data are made of date dtype.
                  Indeed, 'std' columns is NaN value, and it is ignored from resulting dataframe.
        """

        computed_stats = bulk_df.describe(
            datetime_is_numeric=True,
            percentiles=BulkStatistics._percentiles
        )

        computed_stats = computed_stats.astype('string').transpose()
        computed_stats[BulkStatistics._valid_values_label] = catalog.nb_rows
        computed_stats.rename(columns=BulkStatistics._renaming_stats_labels, inplace=True)

        if 'std' not in computed_stats.columns:
            # The standard deviation column 'std' is omitted from df.describe() result when
            # all the dtypes of bulk data are date.
            # To prevent the omission of 'std' column when reading parquet files later on,
            # the creation of 'std' column is manually added.
            computed_stats['std'] = np.nan

        return computed_stats

    def _compute_stats_on_bulk_batch(self, catalog: BulkCatalog, columns: List[str], record_id: str, bulk_uri: str):
        """
        Entrypoint for Dask workers to run statistics computation: fetch pieces of bulk data, compute and save results

        @param catalog: bulk data catalog
        @param columns: selected columns to be computed
        @param record_id: record id on which computation will be performed
        @param bulk_uri: URI of bulk data on which computation will be performed
        """
        bulk_df = self._fetch_bulk_batch(catalog, columns)

        computed_stats = self._compute_statistics_batch(bulk_df, catalog)

        self._save_statistics_batch(computed_stats, record_id, bulk_uri)

    def _save_statistics_batch(self, df_statistics: pd.DataFrame, record_id: str, bulk_id: str):
        """ Save given statistic to parquet file, file path is determined with record_id and bulk_id """

        bulk_statistics_data_path = self._statistics_data_path(record_id, bulk_id)
        self.dask_blob_storage._ensure_dir_tree_exists(bulk_statistics_data_path)

        filename = f"statistics_{df_statistics.index[0]}-{df_statistics.index[-1]}.parquet"
        full_file_path = path_builder.join(bulk_statistics_data_path, filename)

        DataframeSerializerSync.to_parquet(df_statistics,
                                           full_file_path,
                                           storage_options=self.dask_blob_storage._parameters.storage_options)

    def trigger_stats_computation_in_dask(self, columns_count_per_batch, existing_columns,
                                          catalog, record_id, bulk_uri):
        def log_exception(_fut):
            if _fut.exception():
                get_logger().exception(f"Something wrong happened '{_fut.key}'", exc_info=_fut.exception())

        started_tasks = []
        for group_columns in grouper(columns_count_per_batch, existing_columns):
            f = self._submit_with_trace(self._compute_stats_on_bulk_batch,
                                        catalog,
                                        group_columns,
                                        record_id,
                                        bulk_uri,
                                        priority=DASK_BACKGROUND_TASK_PRIORITY)
            f.add_done_callback(log_exception)
            started_tasks.append(f)
        return started_tasks

    async def compute_bulk_statistics(self, record_id: str, bulk_uri: str, record_version: int):
        catalog = await self.dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        existing_columns = catalog.all_columns_dtypes.keys()

        bulk_statistics_path = self._statistics_base_path(record_id, bulk_uri)
        stats_meta_data = StatisticsComputationMeta(computationStartDate=datetime.utcnow(),
                                                    recordId=record_id,
                                                    recordVersion=str(record_version),
                                                    computationStatus=BulkStatisticsStatus.Started)
        try:
            stats_meta_data = await self._push_statistics_meta_file(bulk_statistics_path,
                                                                    stats_meta_data,
                                                                    overwrite_meta_file=False)
        except osdu_storage_exception.ResourceExistsException:
            raise ComputationRunningError("Statistics already computed or in progress")

        nb_rows = catalog.nb_rows
        nb_cols = len(existing_columns)
        columns_count_per_batch = get_columns_count(self._paging_size_per_batch, self._max_cols_per_batch, nb_rows,
                                                    nb_cols)
        stats_computation_tasks = self.trigger_stats_computation_in_dask(columns_count_per_batch, existing_columns,
                                                                         catalog, record_id, bulk_uri)

        stats_meta_data.computation_status = BulkStatisticsStatus.Running
        await self._push_statistics_meta_file(bulk_statistics_path, stats_meta_data, overwrite_meta_file=True)

        asyncio.create_task(self._set_statistics_file_as_complete(stats_computation_tasks,
                                                                  bulk_statistics_path,
                                                                  stats_meta_data))

    async def _set_statistics_file_as_complete(self, _started_tasks, bulk_statistics_path, stats_meta_data):
        """
        Update meta-data file to mark statistics computation as complete

        @param _started_tasks futures of computation tasks run into Dask
        @param bulk_statistics_path: statistics meta file path
        @param stats_meta_data: statistics meta data to be saved
        """

        results = await asyncio.gather(*_started_tasks, return_exceptions=True)
        if any(isinstance(r, BaseException) for r in results):
            stats_meta_data.computation_status = BulkStatisticsStatus.Error
        else:
            stats_meta_data.computation_status = BulkStatisticsStatus.Complete

        await self._push_statistics_meta_file(bulk_statistics_path, stats_meta_data, overwrite_meta_file=True)

    def _fetch_statistics(self, bulk_statistics_data_path: str, columns: List[str]):
        """
        Read parquet files of computed statistics, then filter rows according to given columns.
        """
        statistics_df = pd.read_parquet(bulk_statistics_data_path,
                                        storage_options=self.dask_blob_storage._parameters.storage_options)

        return statistics_df.filter(items=columns, axis=0)

    async def _push_statistics_meta_file(self, bulk_statistics_path: str, stats_meta_data: StatisticsComputationMeta,
                                         overwrite_meta_file: bool):
        """
        Update meta-data file of statistics computation with given status of given stats_meta_data.

        @note: This method aims to be run by main thread, that's why it is async and could use async blob storage client.

        @todo: replace `self.dask_blob_storage._fs.open()` by async blob storage object
        """

        file_path = join(bulk_statistics_path, 'statistics.json')
        json_by_alias_func = functools.partial(stats_meta_data.json, by_alias=True)
        stats_meta_content = await asyncio.get_running_loop().run_in_executor(None, json_by_alias_func)

        if not overwrite_meta_file and self.dask_blob_storage._fs.exists(file_path):
            raise osdu_storage_exception.ResourceExistsException(file_path)

        with self.dask_blob_storage._fs.open(file_path, 'w', overwrite=overwrite_meta_file) as stats_meta_file:
            stats_meta_file.write(stats_meta_content)

        return stats_meta_data

    async def _fetch_statistics_meta_file(self, bulk_statistics_path) -> StatisticsComputationMeta:
        """ Read statistics meta file at given path """

        file_path = join(bulk_statistics_path, 'statistics.json')

        with self.dask_blob_storage._fs.open(file_path, 'r') as stats_meta_file:
            blob_content = stats_meta_file.read()
            return await asyncio.get_running_loop().run_in_executor(None, StatisticsComputationMeta.parse_raw,
                                                                    blob_content)

    async def get_bulk_statistics(self, record_id: str, bulk_uri: str, columns: List[str]) \
            -> (pd.DataFrame, StatisticsComputationMeta):
        """
        @return The statistics data of given record identified by its record_id and bulk_uri

        @param columns: name of columns to be fetched
        @param record_id: record id on which computation has been performed
        @param bulk_uri: URI of bulk data on which computation has been performed
        """

        bulk_statistics_path = self._statistics_base_path(record_id, bulk_uri)
        try:
            statistics_meta = await self._fetch_statistics_meta_file(bulk_statistics_path)
        except (osdu_storage_exception.ResourceNotFoundException, FileNotFoundError):
            raise StatisticsNotFoundError("Statistics do not exist")

        if statistics_meta.computation_status != BulkStatisticsStatus.Complete:
            raise ComputationNotCompleteError("Statistics computation not finished yet")

        catalog = await self.dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        existing_col = catalog.all_columns_dtypes

        if not columns:
            columns = existing_col.keys()
        else:
            if any((wanted_col not in existing_col for wanted_col in columns)):
                raise RequestedCurvesError("Requested curves unknown")

        # todo: find a way to return 400 if requested columns are only not computable columns
        # computable_columns = [col_name for col_name, col_type in existing_col.items()
        #                       if not (col_type == 'bool' or col_type == 'object')]
        # if not computable_columns:
        #     raise Exception("Error 400: not computable columns requested")

        bulk_statistics_data_path = self._statistics_data_path(record_id, bulk_uri)
        stats_df = await self._submit_with_trace(self._fetch_statistics, bulk_statistics_data_path, columns)

        return stats_df, statistics_meta
