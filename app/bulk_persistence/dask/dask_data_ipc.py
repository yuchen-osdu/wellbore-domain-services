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

from os import path, remove
import uuid
import asyncio
from io import BytesIO
from contextlib import asynccontextmanager, contextmanager, suppress
from typing import Union, AsyncGenerator, AsyncContextManager


from app.utils import get_wdms_temp_dir, MiB, GiB, sizeof_fmt
from app.helper.logger import get_logger


"""
Dask data IPC (inter process communication) implementations
=============

This module contains various mechanism to pass data (bytes) between the main process to the dask worker: 
* `DaskNativeDataIPC` uses the native Dask mechanism using dask_client.scatter
* `DaskLocalFileDataIPC` uses temporary local files to transfer data. The main motivation is to reduce the memory while
improving efficiency. Here's a note from Dask: `Note that it is often better to submit jobs to your workers to have them
 load the data rather than loading data locally and then scattering it out to them.`
* `DaskNoneDataIPC` does nothing but forward what is put inside. This is only in case of mono process and as utility for
testing and development.

Data is expected to flow is one for now, from main to worker. In main producer set the data asynchronously using a 
context manager. The `set` method return an handle and getter pointer function. The data can then be fetched using the
 getter function given the handle: and pass the result as argument to the worker:

.. code-block:: python
        async with ipc_data.set(data_to_pass_to_worker) as (ipc_data_handle, ipc_data_getter_func):
            dask.client.submit(some_func, ipc_data_handle, ipc_data_getter_func, ...)


Inside the worker, the data is fetched synchronously as a file_like object:

.. code-block:: python
        with ipc_data_getter_func(ipc_data_handle) as file_like_data:
            actual_data: bytes = file_like_data.read()

"""


async def _real_all_from_async_gen(gen: AsyncGenerator[bytes, None]) -> bytes:
    """ concat all data from an async generator and return the result"""
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
    return b"".join(chunks)


@contextmanager
def ipc_data_getter_from_bytes(ipc_ref):
    """ get data as file_like given data handle as direct bytes. To use with 'with' statement. """
    yield BytesIO(ipc_ref)


@contextmanager
def ipc_data_getter_from_file(ipc_ref):
    """ get data as file_like given data handle from a file. To use with 'with' statement. """
    with open(ipc_ref, 'rb') as f:
        yield f


class DaskNativeDataIPC:
    """
    The class is meant to wrap the way data is transferred from/to a process to/from the Dask worker processes.
    This implementation uses Dask native way using scatter which is not really efficient for significant among of data
    above 2MB.

    `get` is asynchronous and must be used with 'async with statement' providing a tuple (data_handle, getter_func)

    Parameters
    ----------
    dask_client: dask distributed client.

    Examples
    --------

    Must be used with context manager:
    .. code-block:: python
        async def producer_fn():
            data: bytes = ....
            async with DaskDirectIPC(dask_client).set(data) as (data_hdl, getter_func):
                # submit that to Dask workers
                dask_client.submit(worker_fn, data_hdl, getter_func)


        def worker_fn(data_hdl, getter_func):
            with getter_func(data_hdl) as file_like_data:
                data = file_like_data.read()
    """

    ipc_type = 'dask_native'

    def __init__(self, dask_client):
        """ build a dask native ipc """
        self._client = dask_client

    @asynccontextmanager
    async def set(self, data: Union[bytes, AsyncGenerator[bytes, None]]) -> AsyncContextManager:
        if type(data) is not bytes:  # basic type check
            data = await _real_all_from_async_gen(data)

        scattered_data = await self._client.scatter(data)
        yield scattered_data, ipc_data_getter_from_bytes


class DaskLocalFileDataIPC:
    """
    The class is meant to wrap the way data is transferred from/to a process to/from the Dask worker processes.
    This implementation uses Dask native way using scatter which is not really efficient for significant among of data
    above 2MB.
    Files are automatically clearer.

    `get` is asynchronous, `set` is synchronous. `set` returns a read only file-like object

    Parameters
    ----------
    base_folder: local directory where the temporary file will be created. If `None`, will use `get_wdms_temp_dir()`.
    io_chunk_size: on write, size (in bytes) to write before giving back hand to event loop since disk writing is
     synchronous.

    Examples
    --------

    Must be used with context manager:

    .. code-block:: python
        async def producer_fn():
            data: bytes = ....
            async with DaskLocalFileIPC('.').set(data) as (data_hdl, getter_func):
                # submit that to Dask workers
                dask_client.submit(worker_fn, data_hdl, getter_func)


        def worker_fn(data_hdl, getter_func):
            with getter_func(data_hdl) as file_like_data:
                data = file_like_data.read()
    """

    ipc_type = 'local_file'

    total_files_count = 0  # not thread safe but just for monitoring purposes
    total_size_in_file = 0  # not thread safe but just for monitoring purposes

    def __init__(self, base_folder=None, io_chunk_size=50*MiB):
        self._base_folder = base_folder or get_wdms_temp_dir()
        self._io_chunk_size = io_chunk_size

    class _AsyncSetterContextManager:
        # done this way rather than @asynccontextmanager to release memory as soon as it's possible
        def __init__(self, base_folder: str, data: Union[bytes, AsyncGenerator[bytes, None]], chunk_size: int):
            self._base_folder = base_folder
            self._data = data
            self._file_path = None
            self._file_size = 0
            self._io_chunk_size = chunk_size

        def _clean(self):
            # delete file if any
            if self._file_path:
                get_logger().debug(f"IPC data via file, deletion of {self._file_path}")
                with suppress(Exception):
                    remove(self._file_path)

                # keep track of total file and size for monitoring purposes
                DaskLocalFileDataIPC.total_files_count = max(0, DaskLocalFileDataIPC.total_files_count-1)
                DaskLocalFileDataIPC.total_size_in_file = max(0, DaskLocalFileDataIPC.total_size_in_file-self._file_size)

                self._file_path = None

        async def _write_to_file(self, file, chunk_data: bytes) -> int:
            """ write the  """
            if self._io_chunk_size == 0 or len(chunk_data) < self._io_chunk_size:  # write it all at once
                return file.write(chunk_data)

            # loop and release the event loop
            dump_size = self._io_chunk_size
            written_size = 0
            for i in range(0, len(chunk_data), dump_size):
                written_size += file.write(chunk_data[i:i + dump_size])
                # as Disk I/O cannot really be async, read/write one chunk at a time then release the event loop
                await asyncio.sleep(0)
            return written_size

        async def __aenter__(self):
            filepath = path.join(self._base_folder, 'ipc_' + str(uuid.uuid4()))
            try:
                with open(filepath, 'wb') as f:
                    DaskLocalFileDataIPC.total_files_count += 1
                    self._file_path = filepath
                    if type(self._data) is bytes:  # basic type check
                        # data are bytes
                        self._file_size = await self._write_to_file(f, self._data) or 0
                    else:
                        # data is passed as a async generator
                        async for data_chunk in self._data:
                            # async generator provided: iterate on chunks
                            self._file_size += await self._write_to_file(f, data_chunk)
                    self._data = None  # unref so it can be freed

                    get_logger().debug(f"IPC data via file, {self._file_size} bytes written into {self._file_path}")
                    DaskLocalFileDataIPC.total_size_in_file += self._file_size
                    return filepath, ipc_data_getter_from_file
            except:  # clean up file in any case on write failure
                self._clean()
                raise

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self._clean()

    def set(self, data: Union[bytes, AsyncGenerator[bytes, None]]) -> AsyncContextManager:
        self._log_files_stat()
        return self._AsyncSetterContextManager(self._base_folder, data, self._io_chunk_size)

    @classmethod
    def _log_files_stat(cls):
        """ internal log current number of file and total size """
        if cls.total_size_in_file > (5 * GiB):
            get_logger().error(f"unexpected IPC data high usage: {cls.total_size_in_file} files"
                               f" for {sizeof_fmt(cls.total_size_in_file)}")
        elif cls.total_size_in_file > (2 * GiB):
            get_logger().warning(f"IPC data high usage: {cls.total_size_in_file} files"
                                 f" for {sizeof_fmt(cls.total_size_in_file)}")
        elif cls.total_size_in_file > (1 * GiB):
            get_logger().error(f"IPC data usage: {cls.total_size_in_file} files"
                               f" for {sizeof_fmt(cls.total_size_in_file)}")


class DaskNoneDataIPC:
    """ Utility, when no multiprocess, do nothing just pass, get data as it """
    ipc_type = 'none'

    @asynccontextmanager
    async def set(self, data: Union[bytes, AsyncGenerator[bytes, None]]) -> AsyncContextManager:
        if type(data) is not bytes:  # basic type check
            data = await _real_all_from_async_gen(data)
        yield data, ipc_data_getter_from_bytes
