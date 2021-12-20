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
from typing import Awaitable, Callable, List, Optional, Union, AsyncGenerator, Tuple
import uuid

import fsspec
import pandas as pd
import dask.dataframe as dd
from dask.distributed import Client as DaskDistributedClient
import pyarrow.parquet as pa

from osdu.core.api.storage.dask_storage_parameters import DaskStorageParameters

from app.helper.logger import get_logger
from app.helper.traces import with_trace
from app.persistence.sessions_storage import Session
from app.utils import DaskClient, capture_timings
from app.conf import Config

from .dask_worker_plugin import DaskWorkerPlugin
from .errors import BulkRecordNotFound, BulkNotProcessable, internal_bulk_exceptions
from .traces import map_with_trace, submit_with_trace
from .utils import (by_pairs, do_merge, worker_capture_timing_handlers,
                    get_num_rows, set_index, index_union)
from ..dataframe_validators import is_reserved_column_name, DataFrameValidationFunc
from .. import DataframeSerializerSync
from . import storage_path_builder as pathBuilder
from . import session_file_meta as session_meta
from ..bulk_id import new_bulk_id
from .bulk_catalog import BulkCatalog, ChunkGroup, load_bulk_catalog, save_bulk_catalog
from ..mime_types import MimeType
from .dask_data_ipc import DaskNativeDataIPC, DaskLocalFileDataIPC
# TODO TMP
from .dask_bulk_storage_rework import DataframeBasicDescribe, write_bulk_without_session, add_chunk_in_session


def read_with_dask(path: Union[str, List[str]], **kwargs) -> dd.DataFrame:
    """call dask.dataframe.read_parquet with default parameters
    Dask read_parquet parameters:
        chunksize='25M': if chunk are too small, we aggregate them until we reach chunksize
        aggregate_files=True: because we are passing a list of path when commiting a session,
                                aggregate_files is needed when paths are different
    Args:
        path (Union[str, List[str]]): a file, a folder or a list of files
    Returns:
        [dd.DataFrame]: the dask dataframe we read
    """
    arguments = {
        'engine': 'pyarrow-dataset',
        'chunksize': '25M',
        'aggregate_files': True,
    }
    arguments.update(kwargs)

    return dd.read_parquet(path, **arguments)


def _load_index_from_meta(meta, **kwargs):
    return pd.read_parquet(meta.path_with_protocol,
                           engine='pyarrow',
                           columns=[meta.columns[0]],
                           **kwargs).index


def _index_union_tuple(t):
    return index_union(*t)


# TODO TMP
TEMP_FORCE_IPC_WITH_FILE = True


class DaskBulkStorage:
    client: DaskDistributedClient = None
    """ Dask client """

    def __init__(self) -> None:
        """ use `create` to create instance """
        self._parameters = None
        self._fs = None

        # may be also adapted depending of size to data
        if TEMP_FORCE_IPC_WITH_FILE or Config.dask_data_ipc.value == DaskLocalFileDataIPC.ipc_type:
            self._data_ipc = DaskLocalFileDataIPC()
        else:
            self._data_ipc = DaskNativeDataIPC(self.client)

    @classmethod
    async def create(cls, parameters: DaskStorageParameters, dask_client=None) -> 'DaskBulkStorage':
        instance = cls()
        instance._parameters = parameters

        # Initialise the dask client.
        dask_client = dask_client or await DaskClient.create()
        if DaskBulkStorage.client is not dask_client:  # executed only once per dask client
            DaskBulkStorage.client = dask_client

            if parameters.register_fsspec_implementation:
                parameters.register_fsspec_implementation()

            await DaskBulkStorage.client.register_worker_plugin(
                DaskWorkerPlugin,
                name="LoggerWorkerPlugin",
                logger=get_logger(),
                register_fsspec_implementation=parameters.register_fsspec_implementation)

            get_logger().info(f"Distributed Dask client initialized : {DaskBulkStorage.client}")

        instance._fs = fsspec.filesystem(parameters.protocol, **parameters.storage_options)
        return instance

    @property
    def protocol(self) -> str:
        return self._parameters.protocol

    @property
    def base_directory(self) -> str:
        return self._parameters.base_directory

    def _submit_with_trace(self, target_func: Callable, *args, **kwargs):
        return submit_with_trace(self.client, target_func, *args, **kwargs)

    def _map_with_trace(self, target_func: Callable, *args, **kwargs):
        return map_with_trace(self.client, target_func, *args, **kwargs)

    def _relative_path(self, record_id: str, path: str) -> str:
        return pathBuilder.record_relative_path(self.base_directory, record_id, path)

    def _ensure_dir_tree_exists(self, path: str):
        path_wo_protocol, protocol = pathBuilder.remove_protocol(path)

        # on local storage only """
        if protocol == 'file':
            self._fs.mkdirs(path_wo_protocol, exist_ok=True)

    def _read_parquet(self, path: Union[str, List[str]], **kwargs) -> dd.DataFrame:
        """Read a Parquet file into a Dask DataFrame
        Args:
            path (Union[str, List[str]]): a file, a folder or a list of files
            **kwargs dict (of dicts): Passthrough key-word arguments for read backend.
        Returns:
            Future<dd.DataFrame>: dask dataframe
        Dask read_parquet parameters:
            chunksize='25M': if chunk are too small, we aggregate them until we reach chunksize
            aggregate_files=True: because we are passing a list of path when commiting a session,
                                  aggregate_files is needed when paths are different
        """
        return self._submit_with_trace(read_with_dask, path,
                                       storage_options=self._parameters.storage_options,
                                       **kwargs)

    def _load_bulk_from_catalog(self, catalog: BulkCatalog, columns: List[str] = None) -> dd.DataFrame:
        """Load data from information contained in the catalog
            - if the user request columns that does not exists, we ignore them
            - if columns is None, we load all columns
        Returns: Future<dd.dataframe>
        """
        if columns is None:
            columns = catalog.all_columns_dtypes.keys()
        record_path = pathBuilder.record_path(self.base_directory, catalog.record_id, self.protocol)
        files_to_load = catalog.get_paths_for_columns(columns, record_path)
        # read all chunk for requested columns
        def read_parquet_files(f):
            return read_with_dask(f.paths, columns=f.labels, storage_options=self._parameters.storage_options)
        dfs = self._map_with_trace(read_parquet_files, files_to_load)
        if not dfs:
            raise RuntimeError("cannot find requested columns")

        if len(dfs) == 1:
            return dfs[0]

        # if multiple dataframes, concat them together
        dfs = self._map_with_trace(set_index, dfs)
        return self._submit_with_trace(dd.concat, dfs, axis=1, join='outer')

    async def _load_bulk(self, record_id: str, bulk_id: str, columns: List[str] = None) -> dd.DataFrame:
        """Load columns from parquet files in the bulk_path.
        Returns: Future<dd.DataFrame>
        """
        bulk_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)
        catalog = load_bulk_catalog(self._fs, bulk_path)
        if catalog is not None:
            return self._load_bulk_from_catalog(catalog, columns)
        # No catalog means that we can read the folder as a parquet dataset. (legacy behavior)
        return self._read_parquet(bulk_path, columns=columns)

    @with_trace('read_stat')
    async def read_stat(self, record_id: str, bulk_id: str):
        """Returns some meta data about the bulk.
        Raises:
            BulkRecordNotFound: If bulk folder doesn't exists
        """
        catalog = await self.get_bulk_catalog(record_id, bulk_id)
        schema_dict = catalog.all_columns_dtypes
        return {
            "num_rows": catalog.nb_rows,
            "schema": schema_dict
        }

    @capture_timings('load_bulk', handlers=worker_capture_timing_handlers)
    @internal_bulk_exceptions
    @with_trace('load_bulk')
    async def load_bulk(self, record_id: str, bulk_id: str, columns: List[str] = None) -> dd.DataFrame:
        """Returns a dask Dataframe of a record at the specified version.
        Args:
            record_id (str): the record id on which belongs the bulk.
            bulk_id (str): the bulk id to load.
            columns (List[str], optional): columns to load. If None all all available columns. Defaults to None.
        Raises:
            BulkRecordNotFound: If bulk data cannot be found.
        Returns:
            dd.DataFrame: a lazy loaded dask dataframe representing the bulk data.
        """
        try:
            future_df = await self._load_bulk(record_id, bulk_id, columns=columns)
            return await future_df
        except (OSError, RuntimeError) as exp:
            raise BulkRecordNotFound(record_id, bulk_id) from exp

    def _save_with_dask(self, path, dataframe):
        """Save the dataframe to a parquet file(s).
        ddf: dd.DataFrame or Future<dd.DataFrame>
        Returns a Future<None>
        """
        return self._submit_with_trace(dd.to_parquet, dataframe, path,
                                       storage_options=self._parameters.storage_options,
                                       engine='pyarrow', schema="infer", compression='snappy')

    @capture_timings('get_bulk_catalog')
    async def get_bulk_catalog(self, record_id: str, bulk_id: str) -> BulkCatalog:
        bulk_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id)
        catalog = load_bulk_catalog(self._fs, bulk_path)
        if catalog:
            return catalog

        # For legacy bulk, construct a catalog on the fly
        try:
            return await self._build_catalog_from_path(bulk_path, record_id)
        except FileNotFoundError as e:
            raise BulkRecordNotFound(record_id, bulk_id) from e

    @capture_timings('_build_catalog_from_path')
    async def _build_catalog_from_path(self, path: str, record_id: str) -> BulkCatalog:
        """Build a catalog on the fly for folder that don't have a catalog (legacy bulk bolder)
        The method will list all parquet file from the specified folder and build the catalog
        from file metadata. There is an optimization if we detect a folder created by dask.
        Args:
            path (str): Folder that contains parquet files
            record_id (str): recod id from which the catalog belong.
        Raises:
            FileNotFoundError: If path does not exist
        Returns:
            BulkCatalog: [description]
        """
        path, _ = pathBuilder.remove_protocol(path)
        files = self._fs.ls(path)  # raises if path doesn't exists
        is_dask_folder = any((f.endswith('_common_metadata') for f in files))
        parquet_files = (f for f in files if f.endswith('.parquet'))
        files = [path] if is_dask_folder else list(parquet_files)

        futures_datasets = self._map_with_trace(pa.ParquetDataset, files, filesystem=self._fs)
        datasets = await self.client.gather(futures_datasets)

        schemas = (d.read_pandas().schema for d in datasets)

        catalog = BulkCatalog(record_id)
        catalog.nb_rows = max(get_num_rows(d) for d in datasets)

        for file, schema in zip(files, schemas):
            columns = {name: str(dtype) for name, dtype in zip(schema.names, schema.types)
                       if not is_reserved_column_name(name)}
            chunk_group = ChunkGroup(set(columns.keys()), [self._relative_path(record_id, file)], list(columns.values()))
            catalog.add_chunk(chunk_group)

        return catalog

    async def _future_load_index(self, record_id: str, bulk_id: str) -> Awaitable[pd.Index]:
        """load the dataframe index of the specified record"""
        catalog = await self.get_bulk_catalog(record_id, bulk_id)
        if catalog.index_path:
            index_path = pathBuilder.full_path(self.base_directory, record_id, catalog.index_path)
            future_df = self._read_parquet(index_path)
        else: # only read one column to get the index. It doesn't seems possible to get the index directly.
            first_column = next(iter(catalog.all_columns_dtypes))
            future_df = await self._load_bulk(record_id, bulk_id, [first_column])
        return self._submit_with_trace(lambda df: df.index.compute(), future_df)

    @capture_timings('load_index')
    async def load_index(self, record_id: str, bulk_id: str) -> pd.Index:
        """load the dataframe index of the specified record"""
        future_index = await self._future_load_index(record_id, bulk_id)
        return await future_index

    @capture_timings('_build_session_index')
    @with_trace('_build_session_index')
    async def _build_session_index(
        self, chunk_metas: List[session_meta.SessionFileMeta], record_id: str, from_bulk_id: str
    ) -> pd.Index:
        """Combine all chunks indexes + previous version index"""
        # list one file per different index_hash.
        # read chunks indexes from paquet
        indexes = self._map_with_trace(_load_index_from_meta, chunk_metas,
                                       storage_options=self._parameters.storage_options)
        if from_bulk_id:
            # read the index of previous version
            indexes.append(await self._future_load_index(record_id, from_bulk_id))

        # merge all indexes
        while len(indexes) > 1:
            indexes = self._map_with_trace(_index_union_tuple, list(by_pairs(indexes)))
        return await indexes[0]

    @capture_timings('_fill_catalog_columns_info')
    @with_trace('_fill_catalog_columns_info')
    async def _fill_catalog_columns_info(
        self, catalog: BulkCatalog, session_metas, bulk_id: str
    ) -> Optional[BulkCatalog]:
        """ build the catalog from the session."""
        catalog_columns = set(catalog.all_columns_dtypes)

        for chunks_metas in session_meta.get_next_chunk_files(session_metas):
            files = [m.path_with_protocol for m in chunks_metas]
            relative_paths = [self._relative_path(catalog.record_id, f) for f in files]
            # chunks share the same schemas (columns + dtypes) so we get them from the first one
            labels = set(chunks_metas[0].columns)
            dtypes = chunks_metas[0].dtypes
            conflicting_col = catalog_columns.intersection(chunks_metas[0].columns)

            # if some columns already exist in the catalog, merge is needed
            if len(conflicting_col) > 0:
                # filter out the conflicting columns
                labels_dtypes = {label: dtype for label, dtype in zip(labels, dtypes) if label not in conflicting_col}
                labels = set(labels_dtypes.keys())
                dtypes = list(labels_dtypes.values())
                # pb here, wait -> cannot resolve conflict in parallele!
                await self._resolve_conflict_catalog(catalog, bulk_id, files, conflicting_col)

            catalog.add_chunk(ChunkGroup(labels, relative_paths, dtypes))
            catalog_columns.update(chunks_metas[0].columns)

        return catalog

    @capture_timings('_resolve_conflict_catalog')
    @with_trace('_resolve_conflict_catalog')
    async def _resolve_conflict_catalog(
        self, catalog: BulkCatalog, bulk_id: str, files: List[str], cols_to_merge: List[str]
    ) -> None:
        """Merge columns between chunks found in the catalog and chunks files.
        Merged result is save in a new parquet dataset (dask folder) and the catalog is updated with the new path
        Args:
            catalog (BulkCatalog): catalog to update and where input columns are read
            bulk_id (str): record bulk id to retreive the commit path
            files (List[str]): chunk files to merge with chunks from the catalog
            cols_to_merge (List[str]): the columns to merge
        """
        commit_path = pathBuilder.record_bulk_path(self.base_directory, catalog.record_id, bulk_id, self.protocol)

        df1 = self._load_bulk_from_catalog(catalog, columns=cols_to_merge)
        df2 = self._read_parquet(files, columns=cols_to_merge)
        merged_df = self._submit_with_trace(do_merge, df1, df2)

        merged_df_path = pathBuilder.join(commit_path, f'{uuid.uuid4()}.parquet')
        await self._save_with_dask(merged_df_path, merged_df)

        merged_df = await merged_df
        dtypes = [str(dt) for dt in merged_df.dtypes]
        labels = set(merged_df.columns)
        relative_paths = [self._relative_path(catalog.record_id, merged_df_path)]
        chunk_group = ChunkGroup(labels=labels, paths=relative_paths, dtypes=dtypes)
        catalog.change_columns_info(chunk_group)

    @capture_timings('_save_session_index')
    async def _save_session_index(self, path: str, index: pd.Index) -> str:
        index_folder = pathBuilder.join(path, '_wdms_index_')
        self._ensure_dir_tree_exists(index_folder)
        index_path = pathBuilder.join(index_folder, 'index.parquet')

        f_pdf = await self.client.scatter(pd.DataFrame(index=index))
        await self._submit_with_trace(DataframeSerializerSync.to_parquet, f_pdf, index_path,
                                      storage_options=self._parameters.storage_options)

        return index_path

    @capture_timings('session_commit')
    @internal_bulk_exceptions
    @with_trace('session_commit')
    async def session_commit(self, session: Session, from_bulk_id: str = None) -> str:
        """Commit the session
        Args:
            session (Session): The session To commit
            from_bulk_id (str, optional): Bulk id of a previous record version.
                                          Used On session mode update. Defaults to None.
        Raises:
            BulkNotProcessable: If session is empty
        Returns:
            str: identifier of the new bulk
        """
        bulk_id = new_bulk_id()

        chunk_metas = await session_meta.get_chunks_metadata(self._fs, self.base_directory, session)
        if len(chunk_metas) == 0:# there is no files in this session
            raise BulkNotProcessable(message="No data to commit")

        if from_bulk_id:
            # update session: we start from the previous catalog
            catalog = await self.get_bulk_catalog(session.recordId, from_bulk_id)
        else:
            catalog = BulkCatalog(session.recordId)

        commit_path = pathBuilder.record_bulk_path(self.base_directory, session.recordId, bulk_id, self.protocol)

        async def build_and_save_index():
            index = await self._build_session_index(chunk_metas, session.recordId, from_bulk_id)
            index_path = await self._save_session_index(commit_path, index)
            catalog.nb_rows = len(index)
            catalog.index_path = self._relative_path(session.recordId, index_path)

        await asyncio.gather(
            build_and_save_index(),
            self._fill_catalog_columns_info(catalog, chunk_metas, bulk_id)
        )

        save_bulk_catalog(self._fs, commit_path, catalog)
        return bulk_id

    @internal_bulk_exceptions
    @capture_timings('post_data_without_session', handlers=worker_capture_timing_handlers)
    @with_trace('post_data_without_session')
    async def post_data_without_session(self,
                                        data: Union[bytes, AsyncGenerator[bytes, None]],
                                        content_type: MimeType,
                                        df_validator_func: DataFrameValidationFunc,
                                        record_id: str,
                                        bulk_id: Optional[str] = None) -> Tuple[str, DataframeBasicDescribe]:
        """
        process post data outside of a session, delegate the entire work in Dask worker. It constructs the path
        for the bulk in current context, prepare and
        :throw:
            - BulkNotProcessable: in case on invalid input data
            - BulkSaveException: if store operation fails for some reasons
        """

        bulk_id = bulk_id or new_bulk_id()
        bulk_base_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)

        # ensure directory exists for local storage, do nothing on remote storage
        self._ensure_dir_tree_exists(bulk_base_path)

        async with self._data_ipc.set(data) as (data_handle, data_getter):
            data = None  # unref data

            df_describe = await submit_with_trace(self.client,
                                                  write_bulk_without_session,
                                                  data_handle,
                                                  data_getter,
                                                  content_type,
                                                  df_validator_func,
                                                  bulk_base_path,
                                                  self._parameters.storage_options)

        return bulk_id, df_describe

    @internal_bulk_exceptions
    @capture_timings('add_chunk_in_session', handlers=worker_capture_timing_handlers)
    @with_trace('add_chunk_in_session')
    async def add_chunk_in_session(self,
                                   data: Union[bytes, AsyncGenerator[bytes, None]],
                                   content_type: MimeType,
                                   df_validator_func: DataFrameValidationFunc,
                                   record_id: str,
                                   session_id: str,
                                   bulk_id: Optional[str] = None) -> Tuple[str, DataframeBasicDescribe]:
        """
        add a chunk data inside a session, delegate the entire work in Dask worker
        :throw:
            - BulkNotProcessable: in case on invalid input data
            - BulkSaveException: if store operation fails for some reasons
        """

        bulk_id = bulk_id or new_bulk_id()
        base_path = pathBuilder.record_session_path(self.base_directory, session_id, record_id, self.protocol)

        # ensure directory exists for local storage, do nothing on remote storage
        self._ensure_dir_tree_exists(base_path)

        async with self._data_ipc.set(data) as (data_handle, data_getter):
            data = None  # unref data

            df_describe = await submit_with_trace(self.client,
                                                  add_chunk_in_session,
                                                  data_handle,
                                                  data_getter,
                                                  content_type,
                                                  df_validator_func,
                                                  base_path,
                                                  self._parameters.storage_options)

        return bulk_id, df_describe
