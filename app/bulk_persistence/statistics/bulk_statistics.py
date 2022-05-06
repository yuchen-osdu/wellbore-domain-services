import functools
import json
import asyncio
from typing import List, Callable, Iterable
import itertools
from datetime import datetime
from os.path import join
import numpy as np
import pandas as pd

from app.conf import Config
from .models import BulkDataStatisticsMeta, BulkStatisticsStatus

from .. import DataframeSerializerSync
from dask.distributed import fire_and_forget
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
# from app.context import get_ctx
# from osdu.core.api.storage.blob_storage_base import BlobStorageBase
# from app.tenant import resolve_tenant


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


class BulkStatistics:
    dask_blob_storage: DaskBulkStorage = None
    max_number_values = 10_000_000
    max_columns_count = Config.max_columns_return.value

    _stats_api_version = "1"
    _valid_values_label = 'total_count'
    _renaming_stats_labels = {'count': 'count_valid_values'}
    _percentiles = [.10, .5, .90]

    def __init__(self, dask_blob_storage: DaskBulkStorage):
        self.dask_blob_storage = dask_blob_storage

    def _submit_with_trace(self, target_func: Callable, *args, **kwargs):
        return submit_with_trace(self.dask_blob_storage.client, target_func, *args, **kwargs)

    def _get_columns_count(self, nb_rows, nb_cols):
        """
        Return the numbers of columns to be read in bulk files
        to not go over the limit of values bulks data to read at once.
        Maximum number of column is Config.
        """
        total_nb_values = nb_rows * nb_cols
        block_count = max(total_nb_values / self.max_number_values, 1)
        wanted_nb_col = max(int(nb_cols / block_count), 1)
        return min(self.max_columns_count, wanted_nb_col)

    def _record_path(self, record_id: str):
        """
        Return the path to bulk data for record identified by the given record_id.
        It includes protocol in it: file, az, gcs, etc...
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

    def _fetch_bulks(self, catalog, columns):

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
    def _compute_stats(bulk_df: pd.DataFrame, catalog) -> pd.DataFrame:
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

    def _compute(self, catalog: BulkCatalog, columns: List[str], record_id: str, bulk_uri: str):
        """
        Entrypoint forDask workers to run computation: fetch piece of bulk data, compute and save results

        :param catalog: bulk data calog
        :param columns: selected columns to be computed
        :param record_id: record id on which computation will be performed
        :param bulk_uri: URI of bulk data on which computation will be performed

        """
        bulk_df = self._fetch_bulks(catalog, columns)

        computed_stats = self._compute_stats(bulk_df, catalog)

        self._save(computed_stats, record_id, bulk_uri)

    def _save(self, df_statistics: pd.DataFrame, record_id: str, bulk_id: str):
        """ Save given statistic to parquet file, file path is determined with record_id and bulk_id """

        bulk_statistics_data_path = self._statistics_data_path(record_id, bulk_id)
        self.dask_blob_storage._ensure_dir_tree_exists(bulk_statistics_data_path)

        filename = f"statistics_{df_statistics.index[0]}-{df_statistics.index[-1]}.parquet"
        full_file_path = path_builder.join(bulk_statistics_data_path, filename)

        DataframeSerializerSync.to_parquet(df_statistics,
                                           full_file_path,
                                           storage_options=self.dask_blob_storage._parameters.storage_options)

    async def compute_bulk_statistics(self, record_id: str, bulk_uri: str, record_version: int):
        catalog = await self.dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        existing_columns = catalog.all_columns_dtypes.keys()

        bulk_statistics_path = self._statistics_base_path(record_id, bulk_uri)
        stats_meta_data = BulkDataStatisticsMeta(creation_utc_date=datetime.utcnow(),
                                                 record_id=record_id,
                                                 record_version=str(record_version),
                                                 computation_status=BulkStatisticsStatus.Started)
        try:
            stats_meta_data = await self._push_statistics_meta_file(bulk_statistics_path,
                                                                    stats_meta_data,
                                                                    overwrite_meta_file=False)
        except osdu_storage_exception.ResourceExistsException:
            raise ComputationRunningError("Statistics already computed or in progress")

        nb_rows = catalog.nb_rows
        nb_cols = len(existing_columns)
        wanted_columns_number = self._get_columns_count(nb_rows, nb_cols)

        started_tasks = []
        for group_columns in grouper(wanted_columns_number, existing_columns):
            f = self._submit_with_trace(self._compute,
                                        catalog,
                                        group_columns,
                                        record_id,
                                        bulk_uri,
                                        priority=DASK_BACKGROUND_TASK_PRIORITY)
            started_tasks.append(f)

        stats_meta_data.computation_status = BulkStatisticsStatus.Running
        await self._push_statistics_meta_file(bulk_statistics_path, stats_meta_data, overwrite_meta_file=True)

        future = self._submit_with_trace(self._set_statistics_file_as_complete,
                                         started_tasks,
                                         bulk_statistics_path,
                                         stats_meta_data,
                                         priority=DASK_BACKGROUND_TASK_PRIORITY)

        # Dask optimization could not run this task otherwise, it ensures this task is run
        fire_and_forget(future)
        return future

    def _set_statistics_file_as_complete(self, compute_tasks, bulk_statistics_path: str,
                                         stats_meta_data: BulkDataStatisticsMeta):
        """
        Update meta-data file to mark statistics computation as complete

        :param compute_tasks is set as argument but not used, it required to make Dask scheduler aware of the
        predecessor-successor link between `started_tasks` in compute_bulk_statistics() and this method.

        Note: this method is run by a Dask worker => sync required here.
        """

        stats_meta_data.computation_status = BulkStatisticsStatus.Complete
        bulk_statistics_file_path = join(bulk_statistics_path, 'statistics.json')

        with self.dask_blob_storage._fs.open(bulk_statistics_file_path, 'w') as stats_meta_file:
            content = stats_meta_data.json()
            stats_meta_file.write(content)

    def _fetch_statistics(self, bulk_statistics_data_path: str, columns: List[str]):
        """
        Read parquet files of computed statistics, then filter rows according to given columns.
        """
        statistics_df = pd.read_parquet(bulk_statistics_data_path,
                                        storage_options=self.dask_blob_storage._parameters.storage_options)

        return statistics_df.filter(items=columns, axis=0)

    # @staticmethod
    # async def _blob_storage():
    #     """ Return blob storage client on pointing out to the current data partition """
    #     ctx = get_ctx()
    #
    #     # todo: need to double to make sure `get_ctx()` is still viable in case of delayed computation
    #     tenant, storage = await asyncio.gather(
    #         resolve_tenant(ctx.partition_id),
    #         ctx.app_injector.get(BlobStorageBase)
    #     )
    #
    #     return storage, tenant

    async def _push_statistics_meta_file(self, bulk_statistics_path: str, stats_meta_data: BulkDataStatisticsMeta,
                                         overwrite_meta_file: bool):
        """
        Update meta-data file of statistics computation with given status of given stats_meta_data.
        This method aims to be run by main thread, that's why it is async and could use async blob storage client.
        """

        file_path = join(bulk_statistics_path, 'statistics.json')
        stats_meta_content = await asyncio.get_running_loop().run_in_executor(None, stats_meta_data.json)

        # todo: find a way to use blob storage client instead
        # storage, tenant = await self._blob_storage()
        # await storage.upload(tenant,
        #                      overwrite=overwrite_meta_file,
        #                      object_name=file_path,
        #                      file_data=stats_meta_json,
        #                      content_type='application/json',
        #                      )

        if not overwrite_meta_file and self.dask_blob_storage._fs.exists(file_path):
            raise osdu_storage_exception.ResourceExistsException(file_path)

        with self.dask_blob_storage._fs.open(file_path, 'w', overwrite=overwrite_meta_file) as stats_meta_file:
            stats_meta_file.write(stats_meta_content)

        return stats_meta_data

    async def _fetch_statistics_meta_file(self, bulk_statistics_path) -> BulkDataStatisticsMeta:

        file_path = join(bulk_statistics_path, 'statistics.json')

        # todo: find a way to use blob storage client instead
        # storage, tenant = await self._blob_storage()
        # blob_content = await storage.download(tenant, object_name='statistics.json')

        with self.dask_blob_storage._fs.open(file_path, 'r') as stats_meta_file:
            blob_content = stats_meta_file.read()
            return await asyncio.get_running_loop().run_in_executor(None, BulkDataStatisticsMeta.parse_raw,
                                                                    blob_content)

    async def get_bulk_statistics(self, record_id: str, bulk_uri: str, columns: List[str]) \
            -> (pd.DataFrame, BulkDataStatisticsMeta):

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
