from asyncio import iscoroutinefunction, gather
import uuid

from odes_storage.models import *
from osdu.core.api.storage.blob_storage_base import BlobStorageBase


async def no_check_appkey_token(appkey, token):
    # empty method
    pass


class StorageRecordServiceBlobStorage:
    """
    implementation of storage service using blob storage. Security check (appkey & token) responsibility is delegated.
    This is not meant to be used in production but for various testing and debugging purposes. Use injectors to override
    the osdu impl to use this one instead
    """

    def __init__(self,
                 blob_storage: BlobStorageBase,
                 project: str,
                 container: str,
                 auth_check_coro=no_check_appkey_token):
        """
        :param blob_storage:
        :param project: project than will pass to the blob storage calls
        :param container: project than will pass to the blob storage calls
        :param auth_check_coro:
        """
        assert blob_storage
        assert iscoroutinefunction(auth_check_coro)
        self._storage: BlobStorageBase = blob_storage
        self._project: str = project
        self._container: str = container
        self._auth_check = auth_check_coro

    def _build_record_path(self, id: str, data_partition: str):
        return f'{data_partition or "global"}_r_{id.replace(":", "_")}'

    async def _check_auth(self, appkey=None, token=None):
        await self._auth_check(appkey, token)

    async def create_or_update_records(self,
                                       record: List[Record] = None,
                                       data_partition_id: str = None,
                                       appkey: str = None,
                                       token: str = None) -> CreateUpdateRecordsResponse:
        """ record is a bit anonymous, but we do expect 'id' field """
        record_list = record
        await self._check_auth(appkey, token)
        # insert id if new record
        for rec in record_list:
            if rec.id is None:
                rec.id = str(uuid.uuid4())

        await gather(*[
            self._storage.upload(self._project,
                                 self._container,
                                 self._build_record_path(record.id, data_partition_id),
                                 record.json(),
                                 content_type='application/json')
            for record in record_list
        ], return_exceptions=False)  # return_exceptions False means will throw if a single error occurs

        # manual for now
        return CreateUpdateRecordsResponse(recordCount=len(record_list),
                                           recordIds=[record.id for record in record_list])

    async def get_record(self,
                         id: str,
                         data_partition_id: str = None,
                         appkey: str = None,
                         token: str = None) -> Record:
        await self._check_auth(appkey, token)
        object_name = self._build_record_path(id, data_partition_id)
        bin_data = await self._storage.download(self._project, self._container, object_name)
        return Record.parse_raw(bin_data)

    async def get_all_record_versions(self,
                                      id: str,
                                      data_partition_id: str = None,
                                      appkey: str = None,
                                      token: str = None) -> RecordVersions:
        # only one version /latest is supported
        return RecordVersions(recordId=id, versions=[0])

    async def get_record_version(self,
                                 id: str,
                                 version: int,
                                 data_partition_id: str = None,
                                 attribute: List[str] = None,
                                 appkey: str = None,
                                 token: str = None) -> Record:
        # always return the latest
        return await self.get_record(id, data_partition_id, appkey, token)

    async def delete_record(self,
                            id: str,
                            data_partition_id: str = None,
                            appkey: str = None,
                            token: str = None) -> None:
        await self._check_auth(appkey, token)
        object_name = self._build_record_path(id, data_partition_id)
        await self._storage.delete(self._project, self._container, object_name)

    async def get_schema(self, kind, data_partition_id=None, appkey=None, token=None, *args, **kwargs):
        raise NotImplementedError('StorageServiceBlobStorage.get_schema')
