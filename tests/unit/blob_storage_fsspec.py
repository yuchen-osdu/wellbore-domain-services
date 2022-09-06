from typing import Any, Optional, List
from os.path import join
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
    BlobStorageBase over ffspec abstraction
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

    def _build_path(self, tenant, object_name: str):
        if self._base_directory:
            return join(self._base_directory, object_name)
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

    @with_blobstorage_exception(ExceptionMapping)
    async def upload(self, tenant, object_name: str, file_data: Any,
                     *,
                     overwrite: bool = True,
                     if_match=None,
                     if_not_match=None,
                     auth: Optional = None, content_type: str = None, metadata: dict = None,
                     timeout: int = 30, **kwargs) -> Blob:

        full_path = self._build_path(tenant, object_name)
        with self._fs.open(full_path, "wb") as file:
            file.write(file_data)

        return Blob(identifier=object_name,
                    name=object_name,
                    bucket='',
                    metadata={},
                    acl=None, content_type=None, time_created=None, time_updated=None, size=0,
                    etag=object_name)
