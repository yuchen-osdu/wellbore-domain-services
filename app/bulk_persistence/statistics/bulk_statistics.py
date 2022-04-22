import functools
import json
import asyncio
from typing import List, Callable, Iterable
import itertools
from datetime import datetime
from os.path import join
import numpy as np
import pandas as pd

from app.helper.logger import get_logger
from app.conf import Config

from .. import DataframeSerializerSync
from dask.distributed import fire_and_forget
from ..dask.traces import submit_with_trace
from ..dask.bulk_catalog import BulkCatalog
from ..dask.dask_bulk_storage import DaskBulkStorage
from ..dask import storage_path_builder as path_builder
from .exceptions import (
    ComputationRunningError,
    RequestedCurvesError,
    StatisticsNotFoundError,
    ComputationNotCompleteError)

from app.context import get_ctx
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage import exceptions as osdu_storage_exception
from ..tenant_provider import resolve_tenant


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

    def _statistics_folder(self, record_id: str, bulk_id: str):

        base_bulk_base_path = path_builder.record_bulk_path(self.dask_blob_storage.base_directory,
                                                            record_id,
                                                            bulk_id,
                                                            self.dask_blob_storage.protocol)
        bulk_statistics_path = path_builder.join(base_bulk_base_path, f'statistics.v{self._stats_api_version}')
        return bulk_statistics_path

    def _fetch_bulks(self, catalog, columns):

        record_path = self._record_path(catalog.record_id)
        column_paths = catalog.get_paths_for_columns(columns, record_path)

        def read_parquets_same_schema(_col_path):
            _columns, _files_to_load = _col_path.labels, _col_path.paths

            _dfs = (pd.read_parquet(file, columns=_columns) for file in _files_to_load)
            return pd.concat(_dfs, ignore_index=True)

        dfs = (read_parquets_same_schema(col_path) for col_path in column_paths)
        return pd.concat(dfs, ignore_index=True)

    def _compute(self, catalog: BulkCatalog, columns: List[str], record_id: str, bulk_uri: str):
        """
        Note: Column 'std' (standard deviation) can be missing from results, when bulk data are made of date dtype.
              Indeed, 'std' columns is NaN value, and it is ignored from resulting dataframe.
        """
        bulk_df = self._fetch_bulks(catalog, columns)

        computed_stats = bulk_df.describe(
            datetime_is_numeric=True,
            percentiles=BulkStatistics._percentiles
        )
        if 'std' not in computed_stats.index:
            # The standard deviation column 'std' is omitted from df.describe() result when
            # all the dtypes of bulk data are date.
            # To prevent the omission of 'std' column when reading parquet files later on,
            # the creation of 'std' column is manually added.
            computed_stats.loc['std'] = np.nan

        computed_stats = computed_stats.astype('string').transpose()
        computed_stats[BulkStatistics._valid_values_label] = catalog.nb_rows
        computed_stats.rename(columns=BulkStatistics._renaming_stats_labels)

        self._save(computed_stats, record_id, bulk_uri)

    def _save(self, df_statistics, record_id: str, bulk_id: str):
        bulk_statistics_path = join(self._statistics_folder(record_id, bulk_id), 'data')
        self.dask_blob_storage._ensure_dir_tree_exists(bulk_statistics_path)

        filename = f"statistics_{df_statistics.index[0]}-{df_statistics.index[-1]}.parquet"
        full_file_path = path_builder.join(bulk_statistics_path, filename)

        DataframeSerializerSync.to_parquet(df_statistics,
                                           full_file_path,
                                           storage_options=self.dask_blob_storage._parameters.storage_options)

    async def compute_bulk_statistics(self, record_id: str, bulk_uri: str, record_version: int):
        catalog = await self.dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        existing_columns = catalog.all_columns_dtypes.keys()

        bulk_statistics_path = self._statistics_folder(record_id, bulk_uri)
        stats_meta_data = dict(creation_utc_date=datetime.utcnow(),
                               record_id=record_id,
                               record_version=str(record_version),
                               computation_status="started")
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
                                        bulk_uri)
            started_tasks.append(f)

        stats_meta_data.update({"computation_status": "running"})
        await self._push_statistics_meta_file(bulk_statistics_path, stats_meta_data, overwrite_meta_file=True)
        get_logger().info(f"compute statistics: started_tasks {len(started_tasks)}.")

        future = self._submit_with_trace(self._set_statistics_file_as_complete,
                                         started_tasks,
                                         bulk_statistics_path,
                                         dict(stats_meta_data))
        fire_and_forget(future)

    def _set_statistics_file_as_complete(self, compute_tasks, bulk_statistics_path: str, stats_meta_data: dict):

        stats_meta_data.update({"computation_status": "complete"})
        bulk_statistics_file_path = join(bulk_statistics_path, 'statistics.json')

        with self.dask_blob_storage._fs.open(bulk_statistics_file_path, 'w') as stats_meta_file:
            data = json.dumps(stats_meta_data, indent=0, default=str)
            stats_meta_file.write(data)


    def _fetch_statistics(self, bulk_statistics_path: str, columns: List[str]):
        statistics_df = pd.read_parquet(bulk_statistics_path,
                                        storage_options=self.dask_blob_storage._parameters.storage_options)

        return statistics_df.filter(items=columns, axis=0)

    @staticmethod
    async def _blob_storage():
        """ Return blob storage client on pointing out to the current data partition """
        ctx = get_ctx()

        # todo: need to double to make sure `get_ctx()` is still viable in case of delayed computation
        tenant, storage = await asyncio.gather(
            resolve_tenant(ctx.partition_id),
            ctx.app_injector.get(BlobStorageBase)
        )

        return storage, tenant

    async def _push_statistics_meta_file(self, bulk_statistics_path, stats_meta_data, overwrite_meta_file):

        file_path = join(bulk_statistics_path, 'statistics.json')
        json_dumps_with_kwargs = functools.partial(json.dumps, stats_meta_data, indent=0, default=str)
        stats_meta_json = await asyncio.get_running_loop().run_in_executor(None, json_dumps_with_kwargs)

        # todo: find a way to use blob storage client instead
        # storage, tenant = await self._blob_storage()
        # await storage.upload(tenant,
        #                      overwrite=overwrite_meta_file,
        #                      object_name=file_path,
        #                      file_data=stats_meta_json,
        #                      content_type='application/json',
        #                      )

        with self.dask_blob_storage._fs.open(file_path, 'w', overwrite=overwrite_meta_file) as stats_meta_file:
            stats_meta_file.write(stats_meta_json)

        return stats_meta_data

    async def _fetch_statistics_meta_file(self, bulk_statistics_path):

        file_path = join(bulk_statistics_path, 'statistics.json')

        # todo: find a way to use blob storage client instead
        # storage, tenant = await self._blob_storage()
        # blob_content = await storage.download(tenant, object_name='statistics.json')

        with self.dask_blob_storage._fs.open(file_path, 'r') as stats_meta_file:
            blob_content = stats_meta_file.read()
            return await asyncio.get_running_loop().run_in_executor(None, json.loads, blob_content)

    async def get_bulk_statistics(self, record_id: str, bulk_uri: str, columns: List[str]) -> pd.DataFrame:

        bulk_statistics_path = self._statistics_folder(record_id, bulk_uri)
        try:
            statistics_meta = await self._fetch_statistics_meta_file(bulk_statistics_path)
        except osdu_storage_exception.ResourceNotFoundException:
            raise StatisticsNotFoundError("Statistics do not exist")

        if statistics_meta.get('computation_status') != "complete":
            raise ComputationNotCompleteError("Statistics computation not finished yet")

        catalog = await self.dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        existing_col = catalog.all_columns_dtypes

        if not columns:
            columns = existing_col.keys()
        else:
            if any((wanted_col not in existing_col for wanted_col in columns)):
                raise RequestedCurvesError("Requested curves unknown")


        bulk_statistics_path = join(bulk_statistics_path, 'data')
        return await self._submit_with_trace(self._fetch_statistics, bulk_statistics_path, columns)
