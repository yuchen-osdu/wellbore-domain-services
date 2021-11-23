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
from typing import Union, AsyncGenerator


from app.utils import get_wdms_temp_dir


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
context manager and pass the result as argument to the worker:

.. code-block:: python
        async with ipc_data.set(data_to_pass_to_worker) as ipc_data_ref:
            dask.client.submit(some_func, ipc_data_ref, ...)


Inside the worker, the data is fetched synchronously as a file_like object:

.. code-block:: python
        with ipc_data.get(ipc_data_ref) as file_like_data:
            actual_data: bytes = file_like_data.read()

"""


async def _real_all_from_async_gen(gen: AsyncGenerator[bytes, None]) -> bytes:
    """ concat all data from an async generator and return the result"""
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
    return b"".join(chunks)


class DaskNativeDataIPC:
    """
    The class is meant to wrap the way data is transferred from/to a process to/from the Dask worker processes.
    This implementation uses Dask native way using scatter which is not really efficient for significant among of data
    above 2MB.

    `get` is asynchronous, `set` is synchronous. `set` returns a read only file-like object

    Parameters
    ----------
    dask_client: dask distributed client. Can be `None` for data fetcher since ref carries what needed.

    Examples
    --------

    Must be used with context manager:
    .. code-block:: python
        def worker_fn(prepared_data):
            with DaskDirectIPC(dask_client).get(data) as file_like_data:
                data = file_like_data.read()


        async def producer_fn():
            data: bytes = ....
            async with DaskDirectIPC(dask_client).set(data) as prepared_data:
                # submit that to Dask workers
                dask_client.submit(worker_fn, prepared_data)

    """

    ipc_type = 'dask_native'

    def __init__(self, dask_client=None):
        """ build a dask native ipc """
        self._client = dask_client

    @asynccontextmanager
    async def set(self, data: Union[bytes, AsyncGenerator[bytes, None]]):
        if type(data) is not bytes:  # basic type check
            data = await _real_all_from_async_gen(data)

        yield await self._client.scatter(data)

    @contextmanager
    def get(self, ipc_ref):
        yield BytesIO(ipc_ref)


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
        def worker_fn(prepared_data):
            with DaskLocalFileIPC('.').get(data) as file_like_data:
                data = file_like_data.read()


        async def producer_fn():
            data: bytes = ....
            async with DaskLocalFileIPC('.').set(data) as prepared_data:
                # submit that to Dask workers
                dask_client.submit(worker_fn, prepared_data)
    """

    ipc_type = 'local_file'

    def __init__(self, base_folder=None, io_chunk_size=1024*1024):
        self._base_folder = base_folder or get_wdms_temp_dir()
        self._io_chunk_size = io_chunk_size

    async def _write_to_file(self, file, chunk_data: bytes):
        if self._io_chunk_size > 0:
            # loop and release the event loop
            dump_size = self._io_chunk_size
            for i in range(0, len(chunk_data), dump_size):
                file.write(chunk_data[i:i + dump_size])
                # as Disk I/O cannot really be async, read/write 1MB at a time then release the event loop
                await asyncio.sleep(0)
        else:
            # write it all at once
            file.write(chunk_data)

    @asynccontextmanager
    async def set(self, data: Union[bytes, AsyncGenerator[bytes, None]]):
        filepath = path.join(self._base_folder, 'ipc_' + str(uuid.uuid4()))
        try:
            with open(filepath, 'wb') as f:
                if type(data) is bytes:  # basic type check
                    await self._write_to_file(f, data)
                else:
                    async for data_chunk in data:
                        # async generator provided: iterate on chunks
                        await self._write_to_file(f, data_chunk)

                yield filepath
        finally:
            # clean up file in any case
            with suppress(Exception):
                remove(filepath)

    @contextmanager
    def get(self, ipc_ref):
        with open(ipc_ref, 'rb') as f:
            yield f


class DaskNoneDataIPC:
    """ Utility, when no multiprocess, do nothing just pass, get data as it """
    ipc_type = 'none'

    @asynccontextmanager
    async def set(self, data: Union[bytes, AsyncGenerator[bytes, None]]):
        if type(data) is not bytes:  # basic type check
            data = await _real_all_from_async_gen(data)
        yield data

    @contextmanager
    def get(self, ipc_ref):
        yield BytesIO(ipc_ref)
