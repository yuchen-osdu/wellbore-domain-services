import io
from typing import Any, Optional, List
from os.path import join, normpath
import fsspec
from osdu.core.api.storage.blob import Blob
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.exceptions import (
    with_blobstorage_exception,
    ResourceNotFoundException,
    AuthenticationException,
    ResourceExistsException)


class BlobStorageFsspec(BlobStorageBase):
    """
    BlobStorageBase over ffspec abstraction, allowing read/write between component that use ffspec like Dask and
    other component directly base on BlobStorageBase
    WARNING the tenant won't be used, expected to be take into account inside the fs provided
    """

    ExceptionMapping = {
        FileNotFoundError: ResourceNotFoundException,
        FileExistsError: ResourceExistsException,
        PermissionError: AuthenticationException
    }

    def __init__(self, base_directory: Optional[str], protocol: Optional[str], **storage_options):
        self._base_directory = base_directory
        self._fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol or 'file', **storage_options)
        self._protocol = protocol

    def _build_path(self, tenant, object_name: str):
        if self._base_directory:
            object_name = join(self._base_directory, object_name)
        if self._protocol == 'file':
            object_name = normpath(object_name)
            # don't replace volume - there's might be smarter way to do it ...
            object_name = object_name[:3] + object_name[3:].replace(':', '_')
        return object_name

    @with_blobstorage_exception(ExceptionMapping)
    async def delete(self, tenant, object_name: str, *,
                     auth: Optional = None, params: dict = None, timeout: int = 10):
        full_path = self._build_path(tenant, object_name)
        self._fs.delete(full_path)

    @with_blobstorage_exception(ExceptionMapping)
    async def download(self, tenant, object_name: str,
                       *, auth: Optional = None, timeout: int = 10, **kwargs) -> bytes:
        full_path = self._build_path(tenant, object_name)
        with self._fs.open(full_path, "rb") as file:
            return file.read()

    @with_blobstorage_exception(ExceptionMapping)
    async def download_metadata(self, tenant, object_name: str,
                                *, auth: Optional = None, timeout: int = 10, ** kwargs) -> Blob:
        # returns fake
        return Blob(identifier=object_name,
                    name=object_name,
                    bucket='',
                    metadata={},
                    acl=None, content_type=None, time_created=None, time_updated=None, size=0,
                    etag=object_name)

    @with_blobstorage_exception(ExceptionMapping)
    async def list_objects(self, tenant,
                           *, auth: Optional = None, prefix: str = '', page_token: Optional[str] = None,
                           max_result: Optional[int] = None, timeout: int = 10, **kwargs) -> List[str]:
        raise RuntimeError("not implemented: list_objects")

    @staticmethod
    def _preprocess_data(data: Any) -> bytes:  # -> bytes
        if isinstance(data, io.BufferedIOBase):
            return data.read()
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode()
        if isinstance(data, io.TextIOBase):
            return data.read().encode()
        if isinstance(data, io.IOBase):
            return data.read()

        raise TypeError(f'unsupported upload type: "{type(data)}"')

    @with_blobstorage_exception(ExceptionMapping)
    async def upload(self, tenant, object_name: str, file_data: Any,
                     *,
                     overwrite: bool = True,
                     if_match=None,
                     if_not_match=None,
                     auth: Optional = None, content_type: str = None, metadata: dict = None,
                     timeout: int = 30, **kwargs) -> Blob:

        full_path = self._build_path(tenant, object_name)
        data = self._preprocess_data(file_data)

        with self._fs.open(full_path, "wb") as file:
            file.write(data)

        return Blob(identifier=object_name,
                    name=object_name,
                    bucket='',
                    metadata={},
                    acl=None, content_type=None, time_created=None, time_updated=None, size=0,
                    etag=object_name)
