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

import hashlib
import json
import os
import re
from contextlib import suppress
from operator import attrgetter
from typing import List, Optional

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
from app.utils import DaskClient, capture_timings, get_ctx

from .dask_worker_plugin import DaskWorkerPlugin
from .errors import BulkNotFound, BulkNotProcessable, internal_bulk_exceptions
from .traces import wrap_trace_process
from .utils import (by_pairs, do_merge, worker_capture_timing_handlers,
                    get_num_rows, set_index, share_items)
from .session_file_meta import SessionFileMeta, get_output_file_name
from ..dataframe_validators import assert_df_validate, validate_index, columns_not_in_reserved_names
from . import storage_path_builder as pathBuilder
from ..bulk_id import new_bulk_id
from .bulk_catalog import BulkCatalog


def pandas_to_parquet(pdf, path, storage_options):
    return pdf.to_parquet(path, index=True, engine='pyarrow', storage_options=storage_options)


def read_with_pandas(path, storage_options):
    return pd.read_parquet(path, engine='pyarrow', storage_options=storage_options)


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

    def _load(self, path, **kwargs) -> dd.DataFrame:
        """Read a Parquet file into a Dask DataFrame
        path : string or list
        **kwargs: dict (of dicts) Passthrough key-word arguments for read backend.

        read_parquet parameters:
          chunksize='25M': if chunk are too small, we aggregate them until we reach chunksize
          aggregate_files=True: because we are passing a list of path when commiting a session,
                                aggregate_files is needed when paths are different

        Returns:
            Future<dd.DataFrame>
        """
        return self._submit_with_trace(dd.read_parquet, path,
                                       engine='pyarrow-dataset',
                                       storage_options=self._parameters.storage_options,
                                       chunksize='25M',
                                       aggregate_files=True,
                                       **kwargs)

    def _load_bulk_from_catalog(self, catalog: BulkCatalog, record_id: str, columns: List[str] = None):
        """Load data from information contains in the catalog
            - if the user request columns that does not exists, we ignore them
            - if columns is None -> load all columns
        Returns: Future<dd.dataframe>
        """
        columns = catalog.columns.keys() & columns if columns else catalog.columns

        # find columns that we can load together
        root_dir = pathBuilder.record_path(self.base_directory, record_id, self.protocol)
        files_to_load = catalog.get_columns_files_groupped_by_files(columns, root_dir)

        dfs = [self._load(path=f["paths"], columns=f["columns"]) for f in files_to_load]
        if len(dfs) == 1:
            return dfs[0]
        dfs = self._map_with_trace(set_index, dfs)
        return self._submit_with_trace(dd.concat, dfs, axis=1, join='outer')
        #return self._submit_with_trace(join_dataframes, dfs)

    def _load_bulk(self, record_id: str, bulk_id: str, columns: List[str] = None):
        """Load columns from parquet files in the bulk_path.
        Returns: Future<dd.DataFrame>
        """
        bulk_path = pathBuilder.record_bulk_path(
            self.base_directory, record_id, bulk_id, self.protocol)
        catalog = self.get_catalog(bulk_path)
        if catalog is None:
            # No catalog means that we can read the folder as a parquet dataset. (legacy behavior)
            return self._load(bulk_path, columns=columns)
        return self._load_bulk_from_catalog(catalog, record_id, columns)

    @with_trace('read_stat')
    async def read_stat(self, record_id: str, bulk_id: str):
        """Return some meta data about the bulk."""
        file_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id)
        catalog = await self.build_catalog(file_path, record_id)

        schema_dict = {vn: item.dtype for vn, item in catalog.columns.items()}
        return {
            "num_rows": catalog.nb_rows,
            "schema": schema_dict
        }

    def _submit_with_trace(self, target_func, *args, **kwargs):
        """
             Submit given target_func to Distributed Dask workers and add tracing required stuff
        """
        kwargs['span_context'] = get_ctx().tracer.span_context
        kwargs['target_func'] = target_func
        return self.client.submit(wrap_trace_process, *args, **kwargs)

    def _map_with_trace(self, target_func, *args, **kwargs):
        """
             Submit given target_func to Distributed Dask workers and add tracing required stuff
        """
        kwargs['span_context'] = get_ctx().tracer.span_context
        kwargs['target_func'] = target_func
        return self.client.map(wrap_trace_process, *args, **kwargs)

    @capture_timings('load_bulk', handlers=worker_capture_timing_handlers)
    @with_trace('load_bulk')
    async def load_bulk(self, record_id: str, bulk_id: str, columns: List[str] = None) -> dd.DataFrame:
        """Return a dask Dataframe of a record at the specified version."""
        try:
            return await self._load_bulk(record_id, bulk_id, columns=columns)
        except OSError as exp:
            raise BulkNotFound(record_id, bulk_id) from exp

    def _save_with_dask(self, path, dataframe):
        """Save the dataframe to a parquet file(s).
        ddf: dd.DataFrame or Future<dd.DataFrame>
        returns a Future<None>
        """
        return self._submit_with_trace(dask_to_parquet, dataframe, path,
                                       storage_options=self._parameters.storage_options)

    async def _save_with_pandas(self, path, dataframe: dd.DataFrame):
        """Save the dataframe to a parquet file(s).
        pdf: pd.DataFrame or Future<pd.DataFrame>
        returns a Future<None>
        """
        dataframe_scatter = await self.client.scatter(dataframe)
        return await self._submit_with_trace(pandas_to_parquet, dataframe_scatter, path,
                                             self._parameters.storage_options)

    @internal_bulk_exceptions
    @capture_timings('save_blob', handlers=worker_capture_timing_handlers)
    @with_trace('save_blob')
    async def save_blob(self, ddf: dd.DataFrame, record_id: str, bulk_id: str = None):
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
        filename = get_output_file_name(pdf)
        #filename = pathBuilder.build_chunk_filename(pdf)

        session_path = pathBuilder.record_session_path(
            self.base_directory, session.id, session.recordId)

        self._fs.mkdirs(session_path, exist_ok=True)  # only for local
        with self._fs.open(f'{session_path}/{filename}.meta', 'w') as outfile:
            json.dump({
                "columns": list(pdf),
                "dtypes": [str(dt) for dt in pdf.dtypes],
                "nb_rows": len(pdf.index), # TODO remove
                "index_hash": hashlib.sha1(pdf.index.values).hexdigest()
            }, outfile)

        session_path = pathBuilder.add_protocol(session_path, self.protocol)
        await self._save_with_pandas(f'{session_path}/{filename}.parquet', pdf)

    @capture_timings('get_session_parquet_files')
    @with_trace('get_session_parquet_files')
    def get_session_parquet_files(self, session):
        """return the parquet files of the specified session"""
        session_path = pathBuilder.record_session_path(
            self.base_directory, session.id, session.recordId)
        with suppress(FileNotFoundError):
            return [f for f in self._fs.ls(session_path) if f.endswith(".parquet")]
        return []

    def _get_next_files_list(self, session: Session):
        """Group session files in lists of files that can be read directly with dask
        File can be grouped if they have the same columns (shape) and no overlap of indexes
        """
        session_files = [SessionFileMeta(self._fs, f) for f in self.get_session_parquet_files(session)]
        session_files = sorted(session_files, key=attrgetter('time'))
        cache = {}
        columns_in_cache = set()
        while session_files:
            cur, *session_files = session_files
            if cur.shape in cache:
                if any(cur.overlap(f) for f in cache[cur.shape]):
                    yield [f'{self.protocol}://{file.path}' for file in cache[cur.shape]]
                    cache[cur.shape] = [cur]
                else:
                    cache[cur.shape].append(cur)
            else:
                if not columns_in_cache.isdisjoint(cur.columns):
                    match = next(metas[0] for metas in cache.values() if cur.has_common_columns(metas[0]))
                    yield [f'{self.protocol}://{file.path}' for file in cache[match.shape]]
                    columns_in_cache = columns_in_cache.difference(match.columns)
                    del cache[match.shape]
                cache[cur.shape] = [cur]
            columns_in_cache.update(cur.columns)

        for files in cache.values():
            yield [f'{self.protocol}://{file.path}' for file in files]

    def trim_protocol(self, path: str)-> str:
        return path.lstrip(f'{self.protocol}://')

    @capture_timings('save_catalog')
    def save_catalog(self, path: str, catalog: BulkCatalog) -> str:
        path = self.trim_protocol(path)
        meta_path = f'{path}/_meta.json' # TODO catalog name ?
        with self._fs.open(meta_path, 'w') as outfile:
            json.dump(catalog.as_dict(), outfile)

    @capture_timings('get_catalog')
    def get_catalog(self, path: str) -> BulkCatalog:
        path = self.trim_protocol(path)
        meta_path = f'{path}/_meta.json'
        if self._fs.exists(meta_path):
            with self._fs.open(meta_path) as json_file:
                data = json.load(json_file)
                return BulkCatalog.from_dict(data)
        return None

    @capture_timings('build_catalog')
    async def build_catalog(self, path: str, record_id, force_build: bool=False) -> BulkCatalog: # TODO remove force build
        # add record_id/bulk_id ? into the catalog
        path = self.trim_protocol(path)
        if not force_build:
            cat = self.get_catalog(path)
            if cat:
                return cat

        root_dir = pathBuilder.record_path(self.base_directory, record_id)

        files = self._fs.ls(path)
        is_dask_folder = any((f.endswith('_common_metadata') for f in files))
        parquet_files = (f for f in files if f.endswith('.parquet'))
        files = [path] if is_dask_folder else list(parquet_files)
        datasets = await self.client.gather(
            self._map_with_trace(lambda f: pa.ParquetDataset(f, filesystem=self._fs), files))
        relative_paths = (os.path.relpath(f, root_dir) for f in files)

        def is_special_column(name) -> bool:
            """special dask and pandas column '__null_dask_index__', '__index_level_0__'"""
            return name.startswith('__') and name.endswith('__')

        catalog = BulkCatalog()
        catalog.nb_rows = max(get_num_rows(d) for d in datasets)  # TODO check: we may have to call load index ?

        schemas = (d.read_pandas().schema for d in datasets)
        for file, schema in zip(relative_paths, schemas):
            filtered_columns = ((x, str(y)) for x, y in zip(schema.names, schema.types)
                               if not is_special_column(x))
            for name, dtype in filtered_columns:
                catalog.columns.setdefault(name, BulkCatalog.ColumnInfo(
                    paths=[], dtype=dtype)).paths.append(file)
                # if dtype != catalog.columns[name].dtype:
                #     raise # TODO check dtype

        return catalog

    async def load_index(self, record_id: str, bulk_id: str) -> pd.Index:
        """load the dataframe index of the specified record"""
        prev_version_path = pathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)
        cat = await self.build_catalog(prev_version_path, record_id)
        if cat.index_path:
            root_dir = pathBuilder.record_path(self.base_directory, record_id, self.protocol)
            future_df = self._load(f'{root_dir}/{cat.index_path}')
        else: # only read the one column to get the index. It doesn't seems possible to get the index directly.
            first_column = next(iter(cat.columns))
            future_df = self._load_bulk(record_id, bulk_id, [first_column])
        return await self._submit_with_trace(lambda df: df.index.compute(), future_df)

    async def _compute_index_of_session(self, session: Session, from_bulk_id: str) -> pd.Index:
        # list one file per different index.
        metas = (SessionFileMeta(self._fs, f) for f in self.get_session_parquet_files(session))
        indexes_paths = {m.index_hash: m.path for m in metas}.values()
        if len(indexes_paths) == 0:
            return None # there is no files in this session

        def read_parquet_index(path, storage_options) -> pd.Index:
            return read_with_pandas(path, storage_options=storage_options).index

        indexes = [self._submit_with_trace(
            read_parquet_index, f'{self.protocol}://{file}', self._parameters.storage_options)
            for file in indexes_paths]

        if from_bulk_id:
            indexes.append(await self.load_index(session.recordId, from_bulk_id))

        def merge_index(idx1: pd.Index, idx2: Optional[pd.Index]):
            return idx1.union(idx2) if idx2 is not None else idx1

        while len(indexes) > 1:
            indexes = [self._submit_with_trace(merge_index, x,y)
                       for x, y in by_pairs(indexes)]
        return await indexes[0]

    @capture_timings('_build_catalog_from_session')
    async def _build_catalog_from_session(self, session: Session, bulk_id: str, from_bulk_id: str = None) -> Optional[BulkCatalog]:
        """ build the catalog from the session."""
        commit_path = pathBuilder.record_bulk_path(self.base_directory, session.recordId, bulk_id, self.protocol)
        root_dir = pathBuilder.record_path(self.base_directory, session.recordId, self.protocol)

        index = await self._compute_index_of_session(session, from_bulk_id)
        if index is None:
            raise BulkNotProcessable("No data to commit")

        async def save_index(folder, index:pd.Index):
            index_folder = os.path.join(folder, '__index__')
            self._fs.mkdirs(self.trim_protocol(index_folder)) # for local storage
            index_path = os.path.join(index_folder, 'index.parquet')
            await self._save_with_pandas(index_path, pd.DataFrame(index=index))
            return index_path

        index_path = await save_index(commit_path, index)

        catalog = BulkCatalog()
        catalog.index_path = os.path.relpath(index_path, root_dir)
        catalog.nb_rows = len(index)

        if from_bulk_id:
            prev_version_path = pathBuilder.record_bulk_path(
                self.base_directory, session.recordId, from_bulk_id, self.protocol)
            catalog = await self.build_catalog(prev_version_path, session.recordId)

        merge_file_counter = 0
        for files in self._get_next_files_list(session):
            # files share the same schemas so we retrieve the meta data from the first one
            meta = SessionFileMeta(self._fs, files[0])
            rel_files = [os.path.relpath(file, root_dir) for file in files]
            new_entries = {col_name: BulkCatalog.ColumnInfo(paths=rel_files, dtype=dtype)
                           for col_name, dtype in zip(meta.columns, meta.dtypes)}
            # if column exists in the catalog, merge is needed
            if share_items(catalog.columns, new_entries):
                common = catalog.columns.keys() & new_entries
                df1 = self._load_bulk_from_catalog(catalog, session.recordId, columns=common)
                df2 = self._load(files, columns=common)
                merged_df = self._submit_with_trace(do_merge, df1, df2)
                merged_df_path = os.path.join(commit_path, f'part_{merge_file_counter}.parquet')
                merge_file_counter += 1
                # pb here, wait -> cannot resolve conflict in parallele!
                await self._save_with_dask(merged_df_path, merged_df)
                # update new catalog entries with the new path
                rel_files = [os.path.relpath(merged_df_path, root_dir)]
                for colname in common:
                    new_entries[colname].paths = rel_files

            catalog.columns.update(new_entries)

        return catalog

    @capture_timings('session_commit')
    @with_trace('session_commit')
    @internal_bulk_exceptions
    async def session_commit(self, session: Session, from_bulk_id: str = None) -> str:
        """
        Commit a session
        session: the session to commit
        from_bulk_id: id of the bulk to add to seesion. Used when updating a record.
        """
        bulk_id = new_bulk_id()
        commit_path = pathBuilder.record_bulk_path(
            self.base_directory, session.recordId, bulk_id, self.protocol)
        catalog = await self._build_catalog_from_session(session, bulk_id, from_bulk_id)
        if catalog and catalog.columns:
            self.save_catalog(commit_path, catalog)  # TODO async
            return bulk_id  # If no merge is needed, we stop here

        raise BulkNotProcessable("No data to commit")


async def make_local_dask_bulk_storage(base_directory: str) -> DaskBulkStorage:
    params = DaskStorageParameters(protocol='file',
                                   base_directory=base_directory,
                                   storage_options={'auto_mkdir': True})
    return await DaskBulkStorage.create(params)
