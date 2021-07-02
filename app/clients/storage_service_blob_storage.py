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

import uuid
from asyncio import gather, iscoroutinefunction

from app.model import model_utils
from fastapi import FastAPI, HTTPException, status
from odes_storage.models import *
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.exceptions import ResourceNotFoundException
from osdu.core.api.storage.tenant import Tenant
from ulid import ULID


async def no_check_appkey_token(appkey, token):
    # empty method
    pass


class StorageRecordServiceBlobStorage:
    """
    implementation of storage service using blob storage. Security check (appkey & token) responsibility is delegated.
    This is not meant to be used in production but for various testing and debugging purposes. Use injectors to override
    the osdu impl to use this one instead
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

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


    @staticmethod
    def _get_record_folder(id: str, data_partition: str):
        encoded_id = hash(id)
        folder = f'{data_partition or "global"}_r_{encoded_id}'
        return folder

    async def _get_all_version_object(self, id: str, data_partition: str):
        folder = self._get_record_folder(id, data_partition)
        tenant = Tenant(project_id=self._project, bucket_name=self._container, data_partition_id=data_partition)
        return sorted(await self._storage.list_objects(tenant=tenant, prefix=folder))

    async def _build_record_path(self, id: str, data_partition: str, version=None):
        folder = self._get_record_folder(id, data_partition)
        if version:
            return f'{folder}/{version}'
        objects = await self._get_all_version_object(id, data_partition)
        return objects[-1] if objects else None

    async def _check_auth(self, appkey=None, token=None):
        await self._auth_check(appkey, token)

    @staticmethod
    def _get_new_id_for_record(record: Record):
        kind = record.kind.split(':')
        return ':'.join((kind[0], kind[2], uuid.uuid4().hex))

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
                rec.id = self._get_new_id_for_record(rec)# str(uuid.uuid4())
            rec.version = int(ULID())  # generate new version -> ulid is sorted that helps us to know the latest version
        await gather(*[
            self._storage.upload(
                Tenant(project_id=self._project, bucket_name=self._container, data_partition_id=data_partition_id),
                await self._build_record_path(record.id, data_partition_id, version=rec.version),
                model_utils.record_to_json(record),
                content_type='application/json')
            for record in record_list
        ], return_exceptions=False)  # return_exceptions False means will throw if a single error occurs

        # manual for now
        return CreateUpdateRecordsResponse(recordCount=len(record_list),
                                           recordIds=[record.id for record in record_list],
                                           recordIdVersions=[record.version for record in record_list],
                                           skipped_record_ids=[])

    async def get_record_version(self,
                         id: str,
                         version: int,
                         data_partition_id: str = None,
                         appkey: str = None,
                         token: str = None) -> Record:
        await self._check_auth(appkey, token)
        try:
            object_name = await self._build_record_path(id, data_partition_id, version=version)
            if object_name is None:
                raise ResourceNotFoundException("Item not found")
            bin_data = await self._storage.download(
                Tenant(project_id=self._project, bucket_name=self._container, data_partition_id=data_partition_id),
                object_name)
            return Record.parse_raw(bin_data)
        except (FileNotFoundError, ResourceNotFoundException):
            raise HTTPException(status_code=404, detail="Item not found")

    async def get_all_record_versions(self,
                                      id: str,
                                      data_partition_id: str = None,
                                      appkey: str = None,
                                      token: str = None) -> RecordVersions:
        # only one version /latest is supported
        objects = await self._get_all_version_object(id, data_partition_id)
        versions = [o.split('/')[-1] for o in objects]
        return RecordVersions(recordId=id, versions=versions)

    async def get_record(self,
                         id: str,
                         data_partition_id: str = None,
                         attribute: List[str] = None,
                         appkey: str = None,
                         token: str = None) -> Record:
        # return the latest
        return await self.get_record_version(id, None, data_partition_id, appkey, token)

    async def delete_record(self,
                            id: str,
                            data_partition_id: str = None,
                            appkey: str = None,
                            token: str = None) -> None:
        await self._check_auth(appkey, token)
        for object_name in await self._get_all_version_object(id, data_partition_id):
            try:
                await self._storage.delete(
                    Tenant(project_id=self._project, bucket_name=self._container, data_partition_id=data_partition_id),
                    object_name)
            except FileNotFoundError:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    async def get_schema(self, kind, data_partition_id=None, appkey=None, token=None, *args, **kwargs):
        raise NotImplementedError('StorageServiceBlobStorage.get_schema')
