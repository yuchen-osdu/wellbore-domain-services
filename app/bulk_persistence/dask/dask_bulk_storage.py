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
import hashlib
import json
import time
from contextlib import suppress
from functools import wraps
from logging import getLogger
from operator import attrgetter
from osdu.core.api.storage.dask_storage_parameters import DaskStorageParameters

import fsspec
import pandas as pd
from app.bulk_persistence import BulkId
from app.bulk_persistence.dask.errors import BulkNotFound, BulkNotProcessable
from app.bulk_persistence.dask.utils import (SessionFileMeta, by_pairs,
                                             do_merge, set_index,
                                             worker_capture_timing_handlers)
from app.helper.logger import get_logger
from app.helper.traces import with_trace
from app.persistence.sessions_storage import Session
from app.utils import capture_timings, get_wdms_temp_dir
from pyarrow.lib import ArrowException

import dask
import dask.dataframe as dd
from dask.distributed import Client as DaskDistributedClient, WorkerPlugin

dask.config.set({'temporary_directory': get_wdms_temp_dir()})


def handle_pyarrow_exceptions(target):
    @wraps(target)
    async def async_inner(*args, **kwargs):
        try:
            return await target(*args, **kwargs)
        except ArrowException:
            get_logger().exception(f"{target} raised exception")
            raise BulkNotProcessable("Unable to process bulk")

    return async_inner


class DefaultWorkerPlugin(WorkerPlugin):
    def __init__(self, logger=None, register_fsspec_implementation=None) -> None:
        global _LOGGER
        _LOGGER = logger
        self._register_fsspec_implementation = register_fsspec_implementation
        get_logger().debug("WorkerPlugin initialised")
        super().__init__()

    def setup(self, worker):
        self.worker = worker
        if self._register_fsspec_implementation:
            self._register_fsspec_implementation()

    def transition(self, key, start, finish, *args, **kwargs):
        if finish == 'error':
            exc = self.worker.exceptions[key]
            getLogger().exception("Task '%s' has failed with exception: %s" % (key, str(exc)))


class DaskBulkStorage:
    client = None
    """ Dask client """

    lock_client = asyncio.Lock()
    """ used to ensure  """

    def __init__(self):
        """ use `create` to create instance """
        self._parameters = None
        self._fs = None
        
    @classmethod
    async def create(cls, parameters: DaskStorageParameters, dask_client=None) -> 'DaskBulkStorage':
        instance = cls()
        instance._parameters = parameters

        # Initialise the dask client.
        async with DaskBulkStorage.lock_client:
            if not DaskBulkStorage.client:
                DaskBulkStorage.client = dask_client or await DaskDistributedClient(asynchronous=True, processes=True)
                
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
    async def close():  # TODO check for the needs, currently not usage
        async with DaskBulkStorage.lock_client:
            if DaskBulkStorage.client:
                await DaskBulkStorage.client.close()  # or shutdown
                DaskBulkStorage.client = None

    def _encode_record_id(self, record_id: str) -> str:
        return hashlib.sha1(record_id.encode()).hexdigest()

    def _get_base_directory(self, protocol=True):
        return f'{self.protocol}://{self.base_directory}' if protocol else self.base_directory

    def _get_blob_path(self, record_id: str, bulk_id: str, with_protocol=True) -> str:
        """Return the bulk path from the bulk_id."""
        encoded_id = self._encode_record_id(record_id)
        return f'{self._get_base_directory(with_protocol)}/{encoded_id}/bulk/{bulk_id}/data'

    def _build_path_from_session(self, session: Session, with_protocol=True) -> str:
        """Return the session path."""
        encoded_id = self._encode_record_id(session.recordId)
        return f'{self._get_base_directory(with_protocol)}/{encoded_id}/session/{session.id}/data'

    def _load(self, path, **kwargs) -> dd.DataFrame:
        """Read a Parquet file into a Dask DataFrame
        path : string or list
        **kwargs: dict (of dicts) Passthrough key-word arguments for read backend.
        """
        get_logger().debug(f"loading bulk : {path}")
        return self.client.submit(dd.read_parquet, path, engine='pyarrow-dataset',
                                  storage_options=self._parameters.storage_options,
                                  **kwargs)

    def _load_bulk(self, record_id: str, bulk_id: str) -> dd.DataFrame:
        """Return a dask Dataframe of a record at the specified version.
        returns a Future<dd.DataFrame>
        """
        return self._load(self._get_blob_path(record_id, bulk_id))

    @capture_timings('load_bulk', handlers=worker_capture_timing_handlers)
    @with_trace('load_bulk')
    async def load_bulk(self, record_id: str, bulk_id: str) -> dd.DataFrame:
        """Return a dask Dataframe of a record at the specified version."""
        try:
            return await self._load_bulk(record_id, bulk_id)
        except OSError:
            raise BulkNotFound(record_id, bulk_id)  # TODO proper exception

    def _save_with_dask(self, path, ddf):
        """Save the dataframe to a parquet file(s).
        ddf: dd.DataFrame or Future<dd.DataFrame>
        returns a Future<None>
        Note:
            we should be able to change or support other format easily ?
        """
        return self.client.submit(dd.to_parquet, ddf, path, schema="infer",
                                  engine='pyarrow',
                                  storage_options=self._parameters.storage_options)

    def _save_with_pandas(self, path, pdf: dd.DataFrame):
        """Save the dataframe to a parquet file(s).
        pdf: pd.DataFrame or Future<pd.DataFrame>
        returns a Future<None>
        """
        return self.client.submit(pdf.to_parquet, path,
                                  engine='pyarrow',
                                  storage_options=self._parameters.storage_options)

    def _check_incoming_chunk(self, df):
        # TODO should we test if is_monotonic?, unique ?
        if len(df.index) == 0:
            raise BulkNotProcessable("Empty data")

        if not df.index.is_unique:
            raise BulkNotProcessable("Duplicated index found")

        if not df.index.is_numeric() and not isinstance(df.index, pd.DatetimeIndex):
            raise BulkNotProcessable("Index should be numeric or datetime")

    @handle_pyarrow_exceptions
    @capture_timings('save_blob', handlers=worker_capture_timing_handlers)
    async def save_blob(self, ddf: dd.DataFrame, record_id: str, bulk_id: str = None):
        """Write the data frame to the blob storage."""
        # TODO: The new bulk_id should contain information about the way we store the bulk
        # In the future, if we change the way we store chunk it could be useful to deduce it from the bulk_uri
        bulk_id = bulk_id or BulkId.new_bulk_id()

        if isinstance(ddf, pd.DataFrame):
            self._check_incoming_chunk(ddf)
            ddf = dd.from_pandas(ddf, npartitions=1)

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
        shape = hashlib.sha1('_'.join(map(str, pdf)).encode()).hexdigest()
        t = round(time.time() * 1000)
        filename = f'{idx_range}_{t}.{shape}'

        session_path_wo_protocol = self._build_path_from_session(session, with_protocol=False)
        self._fs.mkdirs(session_path_wo_protocol, exist_ok=True)
        with self._fs.open(f'{session_path_wo_protocol}/{filename}.meta', 'w') as outfile:
            json.dump({"columns": list(pdf)}, outfile)

        # could be done asynchronously in the workers but it as a cost
        # we may want to be async if the dataFrame is big
        session_path = self._build_path_from_session(session)
        # await self._save_with_pandas(f'{session_path}/{filename}.parquet', pdf)

        # TODO: Warning this is a sync CPU bound operation
        pdf.to_parquet(f'{session_path}/{filename}.parquet', index=True,
                       storage_options=self._parameters.storage_options, engine='pyarrow')

    @capture_timings('get_session_parquet_files')
    @with_trace('get_session_parquet_files')
    def get_session_parquet_files(self, session):
        session_path = self._build_path_from_session(session, with_protocol=False)
        with suppress(FileNotFoundError):
            session_files = [f for f in self._fs.ls(session_path) if f.endswith(".parquet")]
            return session_files
        return []

    def _get_next_files_list(self, session: Session):
        """Group session files in lists of files that can be read directly with dask
        File can be grouped if they have the same columns (shape) and no overlap of indexes
        """
        session_files = [SessionFileMeta(self._fs, f) for f in self.get_session_parquet_files(session)]
        session_files = sorted(session_files, key=attrgetter('time'))
        while len(session_files) > 0:
            first = session_files.pop(0)
            file_list = [first]
            i = 0
            while i < len(session_files):
                f2 = session_files[i]
                if first.shape == f2.shape:
                    if any(f2.overlap(f) for f in file_list):
                        break
                    file_list.append(session_files.pop(i))
                elif first.has_common_columns(f2):
                    break
                else:
                    i = i + 1

            yield [f'{self.protocol}://{file.path}' for file in file_list]

    @capture_timings('session_commit')
    @with_trace('session_commit')
    @handle_pyarrow_exceptions
    async def session_commit(self, session: Session, from_bulk_id: str = None) -> str:
        dfs = [self._load(pf) for pf in self._get_next_files_list(session)]
        if from_bulk_id:
            dfs.insert(0, self._load_bulk(session.recordId, from_bulk_id))

        if not dfs:
            raise BulkNotProcessable("No data to commit")

        dfs = self.client.map(set_index, dfs)

        while len(dfs) > 1:
            dfs = [self.client.submit(do_merge, a, b) for a, b in by_pairs(dfs)]

        return await self.save_blob(dfs[0], record_id=session.recordId)
	

async def make_local_dask_bulk_storage(base_directory: str) -> DaskBulkStorage:
    params = DaskStorageParameters(protocol='file',
                                   base_directory=base_directory,
                                   storage_options={'auto_mkdir': True})
    return await DaskBulkStorage.create(params)
