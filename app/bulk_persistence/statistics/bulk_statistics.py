from typing import List

import pandas as pd

from ..dask.bulk_catalog import BulkCatalog
from ..dask.dask_bulk_storage import DaskBulkStorage
import itertools
from ..dask import storage_path_builder as path_builder
from .. import DataframeSerializerSync


def grouper(n, iterable):
    n = int(n)
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


class BulkStatistics:
    dask_blob_storage: DaskBulkStorage = None
    max_number_values = 10_000_000
    max_colums_count = 500

    def __init__(self, dask_blob_storage: DaskBulkStorage):
        self.dask_blob_storage = dask_blob_storage

    def _get_columns_count(self, nb_rows, nb_cols):
        """
        Return the numbers of columns to be read in bulk files
        to not go over the limit of values bulks data to read at once
        """
        total_nb_values = nb_rows * nb_cols
        block_count = max(total_nb_values / self.max_number_values, 1)
        wanted_nb_col = int(nb_cols / block_count)
        return min(self.max_colums_count, wanted_nb_col)

    def _bulk_folder(self, record_id: str):
        return path_builder.record_path(self.dask_blob_storage.base_directory,
                                        record_id,
                                        self.dask_blob_storage.protocol)

    def _statistics_folder(self, record_id: str, bulk_id: str):

        base_bulk_base_path = path_builder.record_bulk_path(self.dask_blob_storage.base_directory,
                                                            record_id,
                                                            bulk_id,
                                                            self.dask_blob_storage.protocol)
        bulk_statistics_path = path_builder.join(base_bulk_base_path, 'statistics')
        self.dask_blob_storage._ensure_dir_tree_exists(bulk_statistics_path)
        return bulk_statistics_path

    def _fetch_bulks(self, catalog, columns):

        record_path = self._bulk_folder(catalog.record_id)
        column_paths = catalog.get_paths_for_columns(columns, record_path)

        files_to_load = [col_path.paths for col_path in column_paths]
        files_to_load = itertools.chain.from_iterable(files_to_load)

        dfs = (pd.read_parquet(file, columns=columns) for file in files_to_load)
        return pd.concat(dfs, ignore_index=True)

    def _compute(self, catalog: BulkCatalog, columns: List[str], record_id: str, bulk_uri: str):

        bulk_df = self._fetch_bulks(catalog, columns)
        computed_stats = bulk_df.describe().transpose()

        self._save(computed_stats, record_id, bulk_uri)

    def _save(self, df_statistics, record_id: str, bulk_id: str):
        bulk_statistics_path = self._statistics_folder(record_id, bulk_id)

        filename = f"statistics_{df_statistics.index[0]}.parquet"
        full_file_path = path_builder.join(bulk_statistics_path, filename)

        DataframeSerializerSync.to_parquet(df_statistics,
                                           full_file_path,
                                           storage_options=self.dask_blob_storage._parameters.storage_options)

    async def compute_bulk_statistics(self, record_id: str, bulk_uri: str):
        catalog = await self.dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        existing_columns = catalog.all_columns_dtypes.keys()

        nb_rows = catalog.nb_rows
        nb_cols = len(existing_columns)

        wanted_columns_number = self._get_columns_count(nb_rows, nb_cols)

        started_tasks = []
        for group_columns in grouper(wanted_columns_number, existing_columns):
            f = self.dask_blob_storage._submit_with_trace(self._compute,
                                                          catalog,
                                                          group_columns,
                                                          record_id,
                                                          bulk_uri)
            started_tasks.append(f)

        print("started_tasks", len(started_tasks))

    def _fetch_statistics(self, bulk_statistics_path: str, columns: List[str]):

        parquet_files = [f for f in self.dask_blob_storage._fs.ls(bulk_statistics_path) if f.endswith(".parquet")]
        dfs = (pd.read_parquet(file) for file in parquet_files)
        statistics_df = pd.concat(dfs)

        return statistics_df.filter(items=columns, axis=0)

    async def get_bulk_statistics(self, record_id: str, bulk_uri: str, columns: List[str]) -> pd.DataFrame:

        catalog = await self.dask_blob_storage.get_bulk_catalog(record_id, bulk_uri)
        existing_col = catalog.all_columns_dtypes

        base_bulk_base_path = path_builder.record_bulk_path(self.base_directory, record_id, bulk_uri, self.protocol)
        bulk_statistics_path = path_builder.join(base_bulk_base_path, 'statistics')

        if not columns:
            columns = existing_col.keys()
        else:
            if any((wanted_col not in existing_col for wanted_col in columns)):
                raise Exception("Requested curves unknown")

        return self.dask_blob_storage._submit_with_trace(self._fetch_statistics, bulk_statistics_path, columns)