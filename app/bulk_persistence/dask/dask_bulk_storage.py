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
import time
from contextlib import suppress
from functools import wraps
from operator import attrgetter
from typing import List

import fsspec
import pandas as pd
import pyarrow.parquet as pa
from app.bulk_persistence import BulkId
from app.bulk_persistence.dask.bulk_catalog import BulkCatalog
from app.bulk_persistence.dask.errors import BulkNotFound, BulkNotProcessable
from app.bulk_persistence.dask.traces import wrap_trace_process
from app.bulk_persistence.dask.utils import (SessionFileMeta, by_pairs,
                                             do_merge, set_index, share_items,
                                             worker_capture_timing_handlers)
from app.helper.logger import get_logger
from app.helper.traces import with_trace
from app.persistence.sessions_storage import Session
from app.utils import DaskClient, capture_timings, get_ctx
from osdu.core.api.storage.dask_storage_parameters import DaskStorageParameters
from pyarrow.lib import ArrowException, ArrowInvalid

import dask.dataframe as dd
from dask.distributed import Client as DaskDistributedClient
from dask.distributed import WorkerPlugin, get_client, scheduler


def internal_bulk_exceptions(target):
    """
    Decoration to handler exceptions that should be not exposed to outside world. e.g. Pyarrow or Dask exceptions
    """

    @wraps(target)
    async def async_inner(*args, **kwargs):
        try:
            return await target(*args, **kwargs)
        except ArrowInvalid as e:
            get_logger().exception(f"Pyarrow ArrowInvalid when running {target.__name__}")
            raise BulkNotProcessable(f"Unable to process bulk - {str(e)}")
        except ArrowException:
            get_logger().exception(f"Pyarrow exception raised when running {target.__name__}")
            raise BulkNotProcessable("Unable to process bulk - Arrow")
        except scheduler.KilledWorker:
            get_logger().exception(f"Dask worker raised exception when running '{target.__name__}'")
            raise BulkNotProcessable("Unable to process bulk- Dask")
        except Exception:
            get_logger().exception(f"Unexpected exception raised when running '{target.__name__}'")
            raise

    return async_inner


class DefaultWorkerPlugin(WorkerPlugin):

    def __init__(self, logger=None, register_fsspec_implementation=None) -> None:
        self.worker = None
        global _LOGGER
        _LOGGER = logger

        self._register_fsspec_implementation = register_fsspec_implementation
        super().__init__()
        get_logger().debug("WorkerPlugin initialised")

    def setup(self, worker):
        self.worker = worker
        if self._register_fsspec_implementation:
            self._register_fsspec_implementation()

    def transition(self, key, start, finish, *args, **kwargs):
        if finish == 'error':
            # exc = self.worker.exceptions[key]
            get_logger().exception(f"Task '{key}' has failed with exception")


def pandas_to_parquet(pdf, path, storage_options):
    return pdf.to_parquet(path, index=True, engine='pyarrow', storage_options=storage_options)


def dask_to_parquet(ddf, path, storage_options):
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
                DefaultWorkerPlugin,
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

    @staticmethod
    def encode_record_id(record_id: str) -> str:
        return hashlib.sha1(record_id.encode()).hexdigest()

    def _get_base_directory(self, protocol=True):
        return f'{self.protocol}://{self.base_directory}' if protocol else self.base_directory

    def _get_entity_path(self, record_id: str, with_protocol=True) -> str:
        """Return the entity id path from the record_id."""
        encoded_id = self.encode_record_id(record_id)
        return f'{self._get_base_directory(with_protocol)}/{encoded_id}'

    def _get_bulk_path(self, record_id: str, with_protocol=True) -> str:
        """Return the bulk folder path from the record_id."""
        return f'{self._get_entity_path(record_id, with_protocol)}/bulk'

    def _get_bulk_id_path(self, record_id: str, bulk_id: str, with_protocol=True) -> str:
        """Return the bulk id path from the record_id."""
        return f'{self._get_bulk_path(record_id, with_protocol)}/{bulk_id}'

    def _get_blob_path(self, record_id: str, bulk_id: str, with_protocol=True) -> str:
        """Return the bulk path from the bulk_id."""
        return f'{self._get_bulk_id_path(record_id, bulk_id, with_protocol)}/data'

    def _build_path_from_session(self, session: Session, with_protocol=True) -> str:
        """Return the session path."""
        return f'{self._get_entity_path(session.recordId, with_protocol)}/session/{session.id}/data'

    def _load(self, path, **kwargs) -> dd.DataFrame:
        """Read a Parquet file into a Dask DataFrame
        path : string or list
        **kwargs: dict (of dicts) Passthrough key-word arguments for read backend.

        read_parquet parameters:
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

    def _load_bulk(self, record_id: str, bulk_id: str, columns: List[str] = None):
        """
            load columns from parquet files in the bulk_path
            return a Future<dd.DataFrame>
        """
        bulk_path = self._get_blob_path(record_id, bulk_id)
        catalog = self.get_catalog(bulk_path)
        if catalog is None:
            # if there is no catalog it means that we can read the all folder as a parquet dataset. (legacy behavior)
            return self._load(bulk_path, columns=columns)
        
        schemas = catalog.columns
        
        # if the user request columns that does not exists, we ignore them
        # if columns is None, load all columns
        # TODO should we limit the number of columns to read ?
        columns = set(schemas).intersection(columns) if columns else schemas

        # find columns that we can load together
        root_dir = self._get_entity_path(record_id, with_protocol=True)
        files_to_load = catalog.get_columns_files_groupped_by_files(columns, root_dir)

        dfs = [self._load(path=f["paths"], columns=f["columns"]) for f in files_to_load]
        if len(dfs) == 1:
            return dfs[0]
        dfs = self._map_with_trace(set_index, dfs)
        return self._submit_with_trace(dd.concat, dfs, axis=1, join='outer')
        #return self._submit_with_trace(join_dataframes, dfs)

    @with_trace('read_stat')
    def read_stat(self, record_id: str, bulk_id: str):
        """Return some meta data about the bulk."""
        file_path = self._get_blob_path(record_id, bulk_id, with_protocol=False)
        catalog = self.build_catalog(file_path, record_id)

        schema_dict = {vn: item.dtype for vn, item in catalog.columns.items()}
        return {
            "num_rows": 0, # TODO
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
        except OSError:
            raise BulkNotFound(record_id, bulk_id)  # TODO proper exception

    def _save_with_dask(self, path, ddf):
        """Save the dataframe to a parquet file(s).
        ddf: dd.DataFrame or Future<dd.DataFrame>
        returns a Future<None>
        Note:
            we should be able to change or support other format easily ?
            schema={} instead of 'infer' fixes wrong inference for columns of type string starting with nan values
        """
        return self._submit_with_trace(dask_to_parquet, ddf, path, storage_options=self._parameters.storage_options)

    async def _save_with_pandas(self, path, pdf: dd.DataFrame):
        """Save the dataframe to a parquet file(s).
        pdf: pd.DataFrame or Future<pd.DataFrame>
        returns a Future<None>
        """
        f_pdf = await self.client.scatter(pdf)
        return await self._submit_with_trace(pandas_to_parquet, f_pdf, path,
                                             self._parameters.storage_options)

    @staticmethod
    def _check_incoming_chunk(df):
        # TODO should we test if is_monotonic?, unique ?
        if len(df.index) == 0:
            raise BulkNotProcessable("Empty data")

        if not df.index.is_unique:
            raise BulkNotProcessable("Duplicated index found")

        if not df.index.is_numeric() and not isinstance(df.index, pd.DatetimeIndex):
            raise BulkNotProcessable("Index should be numeric or datetime")

    @internal_bulk_exceptions
    @capture_timings('save_blob', handlers=worker_capture_timing_handlers)
    @with_trace('save_blob')
    async def save_blob(self, ddf: dd.DataFrame, record_id: str, bulk_id: str = None):
        """Write the data frame to the blob storage."""
        bulk_id = bulk_id or BulkId.new_bulk_id()

        if isinstance(ddf, pd.DataFrame):
            self._check_incoming_chunk(ddf)
            ddf = dd.from_pandas(ddf, npartitions=1)
            ddf = await self.client.scatter(ddf)

        path = self._get_blob_path(record_id, bulk_id)
        try:
            await self._save_with_dask(path, ddf)
        except OSError:
            raise BulkNotFound(record_id, bulk_id)  # TODO proper exception
        return bulk_id

    @capture_timings('session_add_chunk')
    @with_trace('session_add_chunk')
    async def session_add_chunk(self, session: Session, pdf: pd.DataFrame):
        self._check_incoming_chunk(pdf)

        # sort column by names
        pdf = pdf[sorted(pdf.columns)]

        # generate a file name sorted by starting index
        # dask reads and sort files by 'natural_key' So the file name impact the final result
        first_idx, last_idx = pdf.index[0], pdf.index[-1]
        if isinstance(pdf.index, pd.DatetimeIndex):
            first_idx, last_idx = pdf.index[0].value, pdf.index[-1].value
        idx_range = f'{first_idx}_{last_idx}'
        shape_str = '_'.join(f'{cn}:{dt}' for cn, dt in pdf.dtypes.items())
        shape = hashlib.sha1(shape_str.encode()).hexdigest()
        cur_time = round(time.time() * 1000)
        filename = f'{idx_range}_{cur_time}.{shape}'  # do not change the name without updating SessionFileMeta

        session_path_wo_protocol = self._build_path_from_session(session, with_protocol=False)
        self._fs.mkdirs(session_path_wo_protocol, exist_ok=True)
        with self._fs.open(f'{session_path_wo_protocol}/{filename}.meta', 'w') as outfile:
            json.dump({
                "columns": list(pdf),
                "dtypes": [str(dt) for dt in pdf.dtypes],
                "nb_rows": len(pdf.index)
            }, outfile)

        session_path = self._build_path_from_session(session)

        await self._save_with_pandas(f'{session_path}/{filename}.parquet', pdf)

    @capture_timings('get_session_parquet_files')
    @with_trace('get_session_parquet_files')
    def get_session_parquet_files(self, session):
        """return the parquet files of the specified session"""
        session_path = self._build_path_from_session(session, with_protocol=False)
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
                    #del cache[cur.shape] # del and recreate the key to maintain ordering
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
    
        for _shape, files in cache.items():
            yield [f'{self.protocol}://{file.path}' for file in files]

    def trim_protocol(self, path: str)-> str:
        return path.lstrip(f'{self.protocol}://')

    @capture_timings('save_catalog')
    def save_catalog(self, path: str, catalog: BulkCatalog) -> str:
        path = self.trim_protocol(path)
        meta_path = f'{path}/_meta.json'
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
    def build_catalog(self, path: str, record_id, force_build: bool = False) -> BulkCatalog:
        path = self.trim_protocol(path)
        if not force_build:
            cat = self.get_catalog(path)
            if cat:
                return cat

        files = [f for f in self._fs.ls(path) if f.endswith('.parquet')]
        datasets = [pa.ParquetDataset(f, filesystem=self._fs) for f in files] # TODO in parallele

        catalog = BulkCatalog()

        #entity_path = self._get_entity_path(record_id, with_protocol=False)
        #assert all(f.startswith(entity_path) for f in files) # TODO security check

        def is_special_column(name) -> bool:
            """special dask and pandas column '__null_dask_index__', '__index_level_0__'"""
            return name.startswith('__') and name.endswith('__')

        root_dir = self._get_entity_path(record_id, with_protocol=False)
        for file, dataset in zip(files, datasets):
            schema = dataset.read_pandas().schema
            schema_dict = {x: str(y) for x, y in zip(
                schema.names, schema.types) if not is_special_column(x)}
            rel_file = os.path.relpath(file, root_dir)
            # TODO check if we can get the number of rows here
 
            for col_name, dtype in schema_dict.items():
                if col_name not in catalog.columns:
                    catalog.columns[col_name] = BulkCatalog.ColumnInfo(paths=[rel_file], dtype=dtype)
                else:
                    catalog.columns[col_name].paths.append(rel_file) # TODO check dtype

        return catalog

    @capture_timings('_try_build_catalog_from_session')
    def _try_build_catalog_from_session(self, session:Session, from_bulk_id: str = None):
        tmp_cat = BulkCatalog()
        if from_bulk_id:
            prev_version_path = self._get_blob_path(session.recordId, from_bulk_id)
            tmp_cat = self.build_catalog(prev_version_path, session.recordId)  # TODO async

        root_dir = self._get_entity_path(session.recordId, with_protocol=True)
        for files in self._get_next_files_list(session):
            rel_files = [os.path.relpath(file, root_dir) for file in files]
            # all the files have the same schemas so we can retrieve the dtype and columns from the first one
            meta = SessionFileMeta(self._fs, files[0])
            # if column already in catalog it means a merge is needed
            if share_items(tmp_cat.columns, meta.columns):#if tmp_cat.columns.keys() & meta.columns:
                return None
            new_entries = {col_name: BulkCatalog.ColumnInfo(paths=rel_files, dtype=dtype)
                           for col_name, dtype in zip(meta.columns, meta.dtypes)}
            #nb_rows = sum((m.nb_rows for m in metas)) # TODO
            tmp_cat.columns.update(new_entries)
        return tmp_cat

    @capture_timings('session_commit')
    @with_trace('session_commit')
    @internal_bulk_exceptions
    async def session_commit(self, session: Session, from_bulk_id: str = None) -> str:
        """
        Commit a session
        session: the session to commit
        from_bulk_id: id of the bulk to add to seesion. Used when updating a record.
        """

        bulk_id = BulkId.new_bulk_id()
        base_path = self._get_blob_path(session.recordId, bulk_id)

        tmp_cat = self._try_build_catalog_from_session(session, from_bulk_id)
        if tmp_cat and tmp_cat.columns:
            self.save_catalog(base_path, tmp_cat)  # TODO async
            return bulk_id  # If no merge is needed, we stop here

        # load all session chunks
        dfs = [self._load(pf) for pf in self._get_next_files_list(session)]
        if not dfs:
            raise BulkNotProcessable("No data to commit")

        # load the data of a precedent version of the record.
        if from_bulk_id:
            dfs.insert(0, self._load_bulk(session.recordId, from_bulk_id))

        def commit_async(chunks: List[dd.DataFrame], base_path, storage_options):
            client = get_client()
            futures = []
            catalog = {}
            while chunks:
                ddf, *chunks = chunks
                if ddf.columns.empty:
                    continue

                path = f'{base_path}/part_{len(futures)}.parquet'
                catalog.update({cn: {'dtype': str(dt), 'paths': [path] } for cn, dt in ddf.dtypes.items()})

                to_merge = [ddf]
                for i, other in enumerate(chunks):
                    common_cols = ddf.columns.intersection(other.columns)
                    if not common_cols.empty:
                        to_merge.append(other[common_cols])
                        chunks[i] = other[other.columns.difference(common_cols)]

                while len(to_merge) > 1:
                    to_merge = [client.submit(do_merge, a, b) for a, b in by_pairs(to_merge)]

                # save to parquet
                futures.append(client.submit(dask_to_parquet, to_merge[0], path, storage_options))

            return futures, catalog

        futures, catalog =  await self._submit_with_trace(commit_async, dfs, base_path,
                                                          self._parameters.storage_options)
        await self.client.gather(futures)

        root_dir = self._get_entity_path(session.recordId, with_protocol=True)
        for col in catalog:
            catalog[col]['paths'] = [os.path.relpath(file, root_dir)
                                     for file in catalog[col]['paths']]

        catalog = BulkCatalog.from_dict({'columns': catalog}) # TODO
        self.save_catalog(base_path, catalog) # TODO async

        return bulk_id

    # @capture_timings('session_commit')
    # @with_trace('session_commit')
    # @internal_bulk_exceptions
    # async def session_commit(self, session: Session, from_bulk_id: str = None) -> str:
    #     """
    #     Commit a session
    #     session: the session to commit
    #     from_bulk_id: id of the bulk to add to seesion. Used when updating a record.
    #     we are merging the session chunks based on a tree reduction algorithm
    #     finish           result             single output
    #         ^          /        \
    #         |        c1          c2        neighbors merge
    #         |       /  \        /  \
    #         |     b1    b2    b3    b4     neighbors merge
    #         ^    / \   / \   / \   / \
    #     start   a1 a2 a3 a4 a5 a6 a7 a8    many inputs
    #     """
    #     # load all session chunks
    #     dfs = [self._load(pf) for pf in self._get_next_files_list(session)]
    #     if not dfs:
    #         raise BulkNotProcessable("No data to commit")

    #     # load the data of a precedent version of the record.
    #     if from_bulk_id:
    #         dfs.insert(0, self._load_bulk(session.recordId, from_bulk_id))

    #     # tree reduction
    #     while len(dfs) > 1:
    #         dfs = [self._submit_with_trace(do_merge, a, b) for a, b in by_pairs(dfs)]

    #     dfs[0] = self._submit_with_trace(pack_array, dfs[0])  # TODO under testing

    #     bulk_id = await self.save_blob(dfs[0], record_id=session.recordId)
    #     await self.plop(session, bulk_id)

    #     return bulk_id


async def make_local_dask_bulk_storage(base_directory: str) -> DaskBulkStorage:
    params = DaskStorageParameters(protocol='file',
                                   base_directory=base_directory,
                                   storage_options={'auto_mkdir': True})
    return await DaskBulkStorage.create(params)
