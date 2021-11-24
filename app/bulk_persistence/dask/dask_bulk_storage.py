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

import json
import os
from typing import Callable, List, Optional, Tuple
import uuid

import fsspec
import pandas as pd
import dask.dataframe as dd
from dask.distributed import Client as DaskDistributedClient
from pyarrow.lib import ArrowException
import pyarrow.parquet as pa

from osdu.core.api.storage.dask_storage_parameters import DaskStorageParameters

from app.helper.logger import get_logger
from app.helper.traces import with_trace
from app.persistence.sessions_storage import Session
from app.utils import DaskClient, capture_timings

from .dask_worker_plugin import DaskWorkerPlugin
from .errors import BulkNotFound, BulkNotProcessable, internal_bulk_exceptions
from .traces import map_with_trace, submit_with_trace
from .utils import (by_pairs, do_merge, worker_capture_timing_handlers,
                    get_num_rows, set_index, index_union)
from ..dataframe_validators import (assert_df_validate, validate_index,
                                    columns_not_in_reserved_names, is_reserved_column_name)
from . import storage_path_builder as pathBuilder
from . import session_file_meta as session_meta
from ..bulk_id import new_bulk_id
from .bulk_catalog import BulkCatalog, load_bulk_catalog, save_bulk_catalog


def pandas_to_parquet(pdf, path, storage_options):
    return pdf.to_parquet(path, index=True, engine='pyarrow', storage_options=storage_options)


def read_with_pandas(path, **kwargs):
    return pd.read_parquet(path, engine='pyarrow', **kwargs)


def read_parquet_index(path, **kwargs) -> pd.Index:
    return read_with_pandas(path, **kwargs).index


def dask_to_parquet(ddf, path, storage_options):
    """ Save dask dataframe to parquet """
    to_parquet_args = {'engine': 'pyarrow',
                       'storage_options': storage_options,
                       'compression': 'snappy',
                       }
    try:
        return dd.to_parquet(ddf, path, **to_parquet_args, schema="infer")
    except ArrowException: # ArrowInvalid
        # In some conditions, the schema is not properly infered. As a workaround, passing schema={} solve the issue.
        return dd.to_parquet(ddf, path, **to_parquet_args, schema={})


class DaskBulkStorage:
    client: DaskDistributedClient = None
    """ Dask client """

    def __init__(self) -> None:
        """ use `create` to create instance """
        self._parameters = None
        self._fs = None

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

    def _read_parquet(self, path: Tuple[str, List[str]], **kwargs) -> dd.DataFrame:
        """Read a Parquet file into a Dask DataFrame
        Args:
            path (Tuple[str, List[str]]): a file, a folder or a list of files
            **kwargs dict (of dicts): Passthrough key-word arguments for read backend.
        Returns:
            Future<dd.DataFrame>: dask dataframe
        Dask read_parquet parameters:
            chunksize='25M': if chunk are too small, we aggregate them until we reach chunksize
            aggregate_files=True: because we are passing a list of path when commiting a session,
                                  aggregate_files is needed when paths are different
        """
        return self._submit_with_trace(dd.read_parquet, path,
                                       engine='pyarrow-dataset',
                                       storage_options=self._parameters.storage_options,
                                       chunksize='25M',
                                       aggregate_files=True,
                                       **kwargs)

    def _load_bulk_from_catalog(self, catalog: BulkCatalog, record_id: str, columns: List[str] = None) -> dd.DataFrame:
        """Load data from information contained in the catalog
            - if the user request columns that does not exists, we ignore them
            - if columns is None, we load all columns
        Returns: Future<dd.dataframe>
        """
        # find columns that we can load together
        columns = catalog.columns.keys() & columns if columns else catalog.columns
        root_dir = pathBuilder.record_path(self.base_directory, record_id, self.protocol)
        files_to_load = catalog.get_paths_for_columns(columns, root_dir)
        # read all chunk for requested columns
        dfs = [self._read_parquet(path=f.paths, columns=f.columns) for f in files_to_load]
        if len(dfs) == 1:
            return dfs[0]
        # if multiple dataframe, concat them together
        dfs = self._map_with_trace(set_index, dfs)
        return self._submit_with_trace(dd.concat, dfs, axis=1, join='outer') # concat or join?

    def _load_bulk(self, record_id: str, bulk_id: str, columns: List[str] = None) -> dd.DataFrame:
        """Load columns from parquet files in the bulk_path.
        Returns: Future<dd.DataFrame>
        """
        bulk_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)
        catalog = load_bulk_catalog(self._fs, bulk_path)
        if catalog is not None:
            return self._load_bulk_from_catalog(catalog, record_id, columns)
        # No catalog means that we can read the folder as a parquet dataset. (legacy behavior)
        return self._read_parquet(bulk_path, columns=columns)

    @with_trace('read_stat')
    async def read_stat(self, record_id: str, bulk_id: str):
        """Returns some meta data about the bulk.
        Raises:
            BulkNotFound: If bulk folder doesn't exists
        """
        catalog = await self.get_bulk_catalog(record_id, bulk_id)

        schema_dict = {vn: item.dtype for vn, item in catalog.columns.items()}
        return {
            "num_rows": catalog.nb_rows,
            "schema": schema_dict
        }

    @capture_timings('load_bulk', handlers=worker_capture_timing_handlers)
    @with_trace('load_bulk')
    async def load_bulk(self, record_id: str, bulk_id: str, columns: List[str] = None) -> dd.DataFrame:
        """Returns a dask Dataframe of a record at the specified version."""
        try:
            return await self._load_bulk(record_id, bulk_id, columns=columns)
        except OSError as exp:
            raise BulkNotFound(record_id, bulk_id) from exp

    def _save_with_dask(self, path, dataframe):
        """Save the dataframe to a parquet file(s).
        ddf: dd.DataFrame or Future<dd.DataFrame>
        Returns a Future<None>
        """
        return self._submit_with_trace(dask_to_parquet, dataframe, path,
                                       storage_options=self._parameters.storage_options)

    async def _save_with_pandas(self, path, dataframe: dd.DataFrame):
        """Save the dataframe to a parquet file(s).
        pdf: pd.DataFrame or Future<pd.DataFrame>
        Returns a Future<None>
        """
        dataframe_scatter = await self.client.scatter(dataframe)
        return await self._submit_with_trace(pandas_to_parquet, dataframe_scatter, path,
                                             self._parameters.storage_options)

    @internal_bulk_exceptions
    @capture_timings('save_bulk', handlers=worker_capture_timing_handlers)
    @with_trace('save_bulk')
    async def save_bulk(self, ddf: dd.DataFrame, record_id: str, bulk_id: str = None):
        """Write the data frame to the blob storage."""
        bulk_id = bulk_id or new_bulk_id()

        if isinstance(ddf, pd.DataFrame):
            assert_df_validate(dataframe=ddf, validation_funcs=[validate_index, columns_not_in_reserved_names])
            ddf = dd.from_pandas(ddf, npartitions=1)
            ddf = await self.client.scatter(ddf)

        path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)
        try:
            await self._save_with_dask(path, ddf)
        except OSError as os_error:
            raise BulkNotFound(record_id, bulk_id) from os_error
        return bulk_id

    @capture_timings('session_add_chunk')
    @with_trace('session_add_chunk')
    async def session_add_chunk(self, session: Session, pdf: pd.DataFrame):
        """add new chunk to the given session"""
        assert_df_validate(dataframe=pdf, validation_funcs=[validate_index, columns_not_in_reserved_names])

        # sort column by names
        pdf = pdf[sorted(pdf.columns)]
        filename = session_meta.generate_chunk_filename(pdf)

        session_path = pathBuilder.record_session_path(
            self.base_directory, session.id, session.recordId)

        self._fs.mkdirs(session_path, exist_ok=True)  # only for local
        with self._fs.open(f'{session_path}/{filename}.meta', 'w') as outfile:
            json.dump(session_meta.build_chunk_metadata(pdf), outfile)

        session_path = pathBuilder.add_protocol(session_path, self.protocol)
        await self._save_with_pandas(f'{session_path}/{filename}.parquet', pdf)

    @capture_timings('get_bulk_catalog')
    async def get_bulk_catalog(self, record_id: str, bulk_id: str) -> BulkCatalog:
        bulk_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id)
        catalog = load_bulk_catalog(self._fs, bulk_path) # TODO async ?
        if catalog:
            return catalog
        # For legacy bulk, construct a catalog on the fly : TODO should we persist it ?
        try:
            return await self._build_catalog_from_path(bulk_path, record_id)
        except FileNotFoundError as e:
            raise BulkNotFound(record_id, bulk_id) from e

    @capture_timings('_build_catalog_from_path')
    async def _build_catalog_from_path(self, path: str, record_id: str) -> BulkCatalog:
        path, _ = pathBuilder.remove_protocol(path)
        files = self._fs.ls(path)  # raise if path doesn't exists
        is_dask_folder = any((f.endswith('_common_metadata') for f in files))
        parquet_files = (f for f in files if f.endswith('.parquet'))
        files = [path] if is_dask_folder else list(parquet_files)

        futures_datasets = [self._submit_with_trace(pa.ParquetDataset, f, self._fs) for f in files]
        datasets = await self.client.gather(futures_datasets)

        root_dir = pathBuilder.record_path(self.base_directory, record_id)
        relative_paths = (os.path.relpath(f, root_dir) for f in files)

        schemas = (d.read_pandas().schema for d in datasets)

        catalog = BulkCatalog()
        catalog.nb_rows = max(get_num_rows(d) for d in datasets)  # TODO check: we may have to call load index ?

        for file, schema in zip(relative_paths, schemas):
            columns = ((name, str(dtype))
                       for name, dtype in zip(schema.names, schema.types)
                       if not is_reserved_column_name(name))
            for name, dtype in columns:
                catalog.add_column_info(name, BulkCatalog.ColumnInfo(paths=[file], dtype=dtype))

        return catalog

    @capture_timings('load_index')
    async def load_index(self, record_id: str, bulk_id: str) -> pd.Index:
        """load the dataframe index of the specified record"""
        catalog = await self.get_bulk_catalog(record_id, bulk_id)
        if catalog.index_path:
            root_dir = pathBuilder.record_path(self.base_directory, record_id, self.protocol)
            future_df = self._read_parquet(f'{root_dir}/{catalog.index_path}')
        else: # only read one column to get the index. It doesn't seems possible to get the index directly.
            first_column = next(iter(catalog.columns)) # TODO if no column ?
            future_df = self._load_bulk(record_id, bulk_id, [first_column])
        return await self._submit_with_trace(lambda df: df.index.compute(), future_df)

    @capture_timings('_build_session_index')
    async def _build_session_index(self, session: Session, from_bulk_id: str) -> pd.Index:
        """Combine all chunks indexes + previous version index"""
        metas = session_meta.get_chunks_metadata(self._fs, self.base_directory, session)
        # list one file per different index_hash.
        chunks_meta_with_different_indexes = {m.index_hash: m for m in metas}.values()
        if len(chunks_meta_with_different_indexes) == 0:
            return None # there is no files in this session
        # read chunks indexes
        indexes = [self._submit_with_trace(read_parquet_index, m.path_with_protocol,
                                           storage_options=self._parameters.storage_options,
                                           columns=[m.columns[0]])
                   for m in chunks_meta_with_different_indexes]
        if from_bulk_id:
            # read the index of previous version
            indexes.append(await self.load_index(session.recordId, from_bulk_id))
        # merge all indexes
        while len(indexes) > 1:
            indexes = [self._submit_with_trace(index_union, x, y) for x, y in by_pairs(indexes)]
        return await indexes[0]

    @capture_timings('_fill_catalog_columns_info')
    async def _fill_catalog_columns_info(self, catalog: BulkCatalog, session: Session, bulk_id: str) -> Optional[BulkCatalog]:
        """ build the catalog from the session."""
        root_dir = pathBuilder.record_path(self.base_directory, session.recordId, self.protocol)
        for files in session_meta.get_next_chunk_files(self._fs, self.base_directory, session):
            # files share the same schemas so we retrieve the meta data from the first one
            meta = session_meta.SessionFileMeta(self._fs, files[0])
            rel_files = [os.path.relpath(file, root_dir) for file in files]
            new_entries = {col_name: BulkCatalog.ColumnInfo(paths=rel_files, dtype=dtype)
                           for col_name, dtype in zip(meta.columns, meta.dtypes)}
            cols_in_catalog = catalog.columns.keys() & new_entries
            if len(cols_in_catalog) > 0:
                # if some columns already exist in the catalog, merge is needed
                # pb here, wait -> cannot resolve conflict in parallele!
                await self._resolve_conflict_catalog(catalog, session.recordId, bulk_id, files, cols_in_catalog)
                new_entries = {k: v for k,v in new_entries.items() if k not in cols_in_catalog}

            catalog.columns.update(new_entries)

        return catalog

    @capture_timings('_resolve_conflict_catalog')
    async def _resolve_conflict_catalog(
        self, catalog: BulkCatalog, record_id: str, bulk_id: str, files: List[str], cols_to_merge: List[str]
    ) -> None:
        """Merge columns between chunks found in the catalog and chunks files.
        Merged result is save in a new parquet dataset (dask folder) and the catalog is updated with the new path
        Args:
            catalog (BulkCatalog): catalog to update and where input columns are read
            record_id (str): record id to retreive path
            bulk_id (str): record bulk id to retreive the commit path
            files (List[str]): chunk files to merge with chunks from the catalog
            cols_to_merge (List[str]): the columns to merge
        """
        commit_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)
        root_dir = pathBuilder.record_path(self.base_directory, record_id, self.protocol)

        df1 = self._load_bulk_from_catalog(catalog, record_id, columns=cols_to_merge)
        df2 = self._read_parquet(files, columns=cols_to_merge)
        merged_df = self._submit_with_trace(do_merge, df1, df2)
        merged_df_path = pathBuilder.join(commit_path, f'{uuid.uuid4()}.parquet')
        await self._save_with_dask(merged_df_path, merged_df)
        rel_files = [os.path.relpath(merged_df_path, root_dir)]
        for colname in cols_to_merge:
            catalog.columns[colname].paths = rel_files # TODO dtype ?

    @capture_timings('_save_session_index')
    async def _save_session_index(self, path: str, index: pd.Index) -> str:
        index_folder = os.path.join(path, '__index__')
        self._fs.mkdirs(pathBuilder.remove_protocol(index_folder)[0]) # for local storage
        index_path = os.path.join(index_folder, 'index.parquet')
        await self._save_with_pandas(index_path, pd.DataFrame(index=index))
        return index_path

    @capture_timings('session_commit')
    @with_trace('session_commit')
    @internal_bulk_exceptions
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
        commit_path = pathBuilder.record_bulk_path(self.base_directory, session.recordId, bulk_id, self.protocol)
        root_dir = pathBuilder.record_path(self.base_directory, session.recordId, self.protocol)

        index = await self._build_session_index(session, from_bulk_id)
        if index is None:
            raise BulkNotProcessable("No data to commit")

        if from_bulk_id:
            # update session: we start from the previous catalog
            catalog = await self.get_bulk_catalog(session.recordId, from_bulk_id)
        else:
            catalog = BulkCatalog()


        catalog.nb_rows = len(index)
        index_path = await self._save_session_index(commit_path, index)
        catalog.index_path = os.path.relpath(index_path, root_dir)

        await self._fill_catalog_columns_info(catalog, session, bulk_id)
        save_bulk_catalog(self._fs, commit_path, catalog)  # TODO async
        return bulk_id


async def make_local_dask_bulk_storage(base_directory: str) -> DaskBulkStorage:
    params = DaskStorageParameters(protocol='file',
                                   base_directory=base_directory,
                                   storage_options={'auto_mkdir': True})
    return await DaskBulkStorage.create(params)
