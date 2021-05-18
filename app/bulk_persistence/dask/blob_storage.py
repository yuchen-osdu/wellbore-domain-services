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
import json
from abc import ABC, abstractmethod
from operator import attrgetter

import dask
import dask.dataframe as dd
import fsspec
import pandas as pd
from app.bulk_persistence import BulkId
from app.bulk_persistence.dask.errors import BulkNotProcessable, BulkNotFound
from app.bulk_persistence.dask.utils import SessionFileMeta, set_index, do_merge, by_pairs
from app.helper.logger import get_logger
from app.helper.traces import with_trace
from app.persistence.sessions_storage import Session
from app.utils import capture_timings, get_wdms_temp_dir
from dask.distributed import Client

dask.config.set({'temporary_directory': get_wdms_temp_dir()})


class DaskBlobStorageBase(ABC):
    @abstractmethod
    async def build_dask_blob_storage(self, tenant):
        raise NotImplementedError('DaskBlobStorageBase.build_dask_blob_storage')


class DaskBlobStorageLocal(DaskBlobStorageBase):
    """Instantiate a DaskDriverBlobStorage with a local file system."""

    def __init__(self, base_directory) -> None:
        self._base_directory = base_directory

    async def build_dask_blob_storage(self, tenant):
        base_directory = f'{self._base_directory}/{tenant.data_partition_id}'
        _dask = DaskDriverBlobStorage(protocol='file',
                                      base_directory=base_directory,
                                      storage_options={'auto_mkdir': True})
        await _dask.init_client()  # TODO should not be init here
        get_logger().debug(f"DASK_CLIENT: {_dask.client}")
        return _dask


class DaskDriverBlobStorage:
    client = None
    lock_client = None

    def __init__(self, protocol, base_directory, storage_options) -> None:
        if DaskDriverBlobStorage.lock_client is None:
            DaskDriverBlobStorage.lock_client = asyncio.Lock()
        self._storage_options = storage_options
        self._protocol = protocol
        self._base_directory = base_directory
        self._fs = fsspec.filesystem(protocol, **self._storage_options)

    @staticmethod
    async def close():
        async with DaskDriverBlobStorage.lock_client:
            if DaskDriverBlobStorage.client:
                await DaskDriverBlobStorage.client.close()  # or shutdown
                DaskDriverBlobStorage.client = None

    @staticmethod
    async def init_client():
        async with DaskDriverBlobStorage.lock_client:
            """Initialise the dask client. Returns False if client was already initialized"""
            if not DaskDriverBlobStorage.client:
                DaskDriverBlobStorage.client = await Client(asynchronous=True, processes=True)
                return True
        return False

    def _get_base_directory(self, protocol=True):
        return f'{self._protocol}://{self._base_directory}' if protocol else self._base_directory

    def _get_blob_path(self, bulk_id, protocol=True) -> str:
        """Return the bulk path from the bulk_id."""
        return f'{self._get_base_directory(protocol)}/{bulk_id}'

    def _build_path_from_session(self, session: Session, protocol=True) -> str:
        """Return the session path."""
        return f'{self._get_base_directory(protocol)}/session-{session.id}'

    def _load(self, path, **kwargs) -> dd.DataFrame:
        """Read a Parquet file into a Dask DataFrame
        path : string or list
        **kwargs: dict (of dicts) Passthrough key-word arguments for read backend.
        """
        return self.client.submit(dd.read_parquet, path, engine='pyarrow-dataset',
                                  storage_options=self._storage_options,
                                  **kwargs)

    def _load_bulk(self, bulk_id) -> dd.DataFrame:
        """Return a dask Dataframe of a record at the specified version.
        returns a future<dd.DataFrame>
        """
        return self._load(self._get_blob_path(bulk_id))

    async def load_bulk(self, bulk_id) -> dd.DataFrame:
        """Return a dask Dataframe of a record at the specified version."""
        try:
            return await self._load_bulk(bulk_id)
        except OSError:
            raise BulkNotFound(bulk_id)  # TODO proper exception

    def _save_with_dask(self, path, ddf):
        """Save the dataframe to a parquet file(s).
        ddf: dd.DataFrame or future<dd.DataFrame>
        returns a future<None>
        Note:
            we should be able to change or support other format easily ?
        """
        return self.client.submit(dd.to_parquet, ddf, path, schema="infer",
                                  engine='pyarrow',
                                  storage_options=self._storage_options)

    def _save_with_pandas(self, path, pdf: dd.DataFrame):
        """Save the dataframe to a parquet file(s).
        pdf: pd.DataFrame or future<pd.DataFrame>
        returns a future<None>
        """
        return self.client.submit(pdf.to_parquet, path, storage_options=self._storage_options)

    def _check_incoming_chunk(self, df):
        # TODO should we test if is_monotonic?, unique ?
        if len(df.index) == 0:
            raise BulkNotProcessable("Empty data")

        if not df.index.is_unique:
            raise BulkNotProcessable("Duplicated index found")

        if not df.index.is_numeric() and not isinstance(df.index, pd.DatetimeIndex):
            raise BulkNotProcessable("Index should be numeric or datetime")

    async def save_blob(self, ddf: dd.DataFrame, bulk_id: str = None):
        """Write the data frame to the blob storage."""
        # TODO: The new bulk_id should contain information about the way we store the bulk
        # In the future, if we change the way we store chunk it could be useful to deduce it from the bulk_uri
        bulk_id = bulk_id or BulkId.new_bulk_id()

        if isinstance(ddf, pd.DataFrame):
            self._check_incoming_chunk(ddf)
            ddf = dd.from_pandas(ddf, npartitions=1)

        path = self._get_blob_path(bulk_id)
        try:
            await self._save_with_dask(path, ddf)
        except OSError:
            raise BulkNotFound(bulk_id)  # TODO proper exception
        return bulk_id

    @capture_timings('session_add_chunk')
    @with_trace('session_add_chunk')
    async def session_add_chunk(self, session: Session, pdf: pd.DataFrame):
        import hashlib
        import time

        self._check_incoming_chunk(pdf)

        # sort column by names
        pdf = pdf[sorted(pdf.columns)]

        # generate a file name sorted by starting index
        # dask reads and sort files by 'natural_key' So the file name impact the final result
        first_idx, last_idx = pdf.index[0], pdf.index[-1]
        if isinstance(pdf.index, pd.DatetimeIndex):
            first_idx, last_idx = pdf.index[0].value, pdf.index[-1].value
        idx_range = f'{first_idx}_{last_idx}'
        shape = hashlib.sha256('_'.join(map(str, pdf)).encode()).hexdigest()
        t = round(time.time() * 1000)
        filename = f'{idx_range}_{t}.{shape}'

        session_path_wo_protocol = self._build_path_from_session(session, protocol=False)
        self._fs.mkdirs(session_path_wo_protocol, exist_ok=True)
        with self._fs.open(f'{session_path_wo_protocol}/{filename}.meta', 'w') as outfile:
            json.dump({"columns": list(pdf)}, outfile)

        # could be done asynchronously in the workers but it as a cost
        # we may want to be async if the dataFrame is big
        session_path = self._build_path_from_session(session)
        # await self._save_with_pandas(f'{session_path}/{filename}.parquet', pdf)
        pdf.to_parquet(f'{session_path}/{filename}.parquet', index=True,
                       storage_options=self._storage_options, engine='pyarrow')

    @capture_timings('get_session_parquet_files')
    @with_trace('get_session_parquet_files')
    def get_session_parquet_files(self, session):
        session_path = self._build_path_from_session(session, protocol=False)
        return self._fs.glob(f'{session_path}/*.parquet')

    def _get_next_files_list(self, session: Session):
        """Group session files in lists of files that can be read directly with dask
        File can be groupped if they have the same columns (shape) and no overlap of indexes
        """
        session_files = [SessionFileMeta(self._fs, f) for f in self.get_session_parquet_files(session)]
        session_files = sorted(session_files, key=attrgetter('time'))
        while len(session_files) > 0:
            first = session_files.pop(0)
            L = [first]
            i = 0
            while i < len(session_files):
                f2 = session_files[i]
                if first.shape == f2.shape:
                    if any(f2.overlap(f) for f in L):
                        break
                    L.append(session_files.pop(i))
                elif first.has_common_columns(f2):
                    break
                else:
                    i = i + 1

            yield [f'{self._protocol}://{file.path}' for file in L]

    @capture_timings('session_commit')
    @with_trace('session_commit')
    async def session_commit(self, session: Session, from_bulk_id: str = None) -> str:
        dfs = [self._load(pf) for pf in self._get_next_files_list(session)]
        if from_bulk_id:
            dfs.insert(0, self._load_bulk(from_bulk_id))

        if not dfs:
            raise BulkNotProcessable("No data to commit")

        dfs = [self.client.submit(set_index, df1) for df1 in dfs]

        while len(dfs) > 1:
            dfs = [self.client.submit(do_merge, a, b) for a, b in by_pairs(dfs)]

        return await self.save_blob(dfs[0])
