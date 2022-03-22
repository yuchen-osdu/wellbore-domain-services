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

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage

from app.conf import Config
from app.helper.logger import get_logger

from .app_injector import AppInjector, AppInjectorModule, WithLifeTime


from app.clients import StorageRecordServiceClient
from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.clients.search_service_client import SearchServiceClient
from app.clients import make_search_client, make_storage_record_client
from app.persistence.sessions_storage import SessionsStorage

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.dask_bulk_storage_local import make_local_dask_bulk_storage


class MainInjector(AppInjectorModule):
    """
    Gather sub injectors, dependency common to any type of deployment and then overriders.
    """

    def configure(self, app_injector: AppInjector):
        logger = get_logger()

        app_injector.register(
            StorageRecordServiceClient,
            self.build_storage_service_client,
            WithLifeTime.Singleton()
        )

        app_injector.register(
            SearchServiceClient,
            self.build_search_service_client,
            WithLifeTime.Singleton()
        )

        # TODO use constants
        # switch gcp/azure
        if Config.cloud_provider.value == 'az':
            from app.injector.az_injector import AzureInjector
            logger.info('using az injector')
            AzureInjector().configure(app_injector)

        if Config.cloud_provider.value == 'gcp':
            from app.injector.gcp_injector import GCPInjector
            logger.info('using gcp injector')
            GCPInjector().configure(app_injector)

        if Config.cloud_provider.value == 'ibm':
            from app.injector.ibm_injector import IBMInjector
            logger.info('using ibm injector')
            IBMInjector().configure(app_injector)

        if Config.cloud_provider.value == 'aws':
            from app.injector.aws_injector import AwsInjector
            logger.info('using aws injector')
            AwsInjector().configure(app_injector)

        async def make_sessions_storage():
            return SessionsStorage(await app_injector.get(BlobStorageBase))

        app_injector.register(SessionsStorage, make_sessions_storage)

        # run overriders
        self.overriders(app_injector)

    def overriders(self, app_injector: AppInjector):
        """ defined here any overrider """
        logger = get_logger()

        if Config.dev_mode.value:
            storage_path: str = Config.get('USE_INTERNAL_STORAGE_SERVICE_WITH_PATH')
            if storage_path:
                logger.warning(f'overriding storage service using localfs blob storage {storage_path}')
                app_injector.register(StorageRecordServiceClient,
                                      self.make_storage_service_on_localfs_blob_storage_builder(storage_path))

            blob_storage_localfs: str = Config.get('USE_LOCALFS_BLOB_STORAGE_WITH_PATH')
            if blob_storage_localfs:
                async def _blob_storage_builder():
                    return LocalFSBlobStorage(directory=blob_storage_localfs)

                logger.warning(f'overriding blob storage to use local fs on path ' + blob_storage_localfs)
                app_injector.register(BlobStorageBase, _blob_storage_builder)

                async def _dask_blob_storage_builder() -> DaskBulkStorage:
                    return await make_local_dask_bulk_storage(base_directory=blob_storage_localfs)

                app_injector.register(DaskBulkStorage, _dask_blob_storage_builder)
                logger.warning(f'overriding DASK blob storage to use local fs on path ' + blob_storage_localfs)


    @staticmethod
    def make_storage_service_on_localfs_blob_storage_builder(path: str):
        """
        create a builder to instantiate a storage service based on local
        :param path: local path to the folder where to store blobs/files
        :return async builder
        """
        import os
        assert os.path.exists(path), path + ' not found'
        return MainInjector.make_storage_service_on_blob_storage_builder(
            LocalFSBlobStorage(directory=path), project='p', container='c'
        )

    @staticmethod
    def make_storage_service_on_blob_storage_builder(blob_storage, project: str, container: str):
        """ instantiate a storage service based on the given blob storage """

        async def _build_it(*args, **kwargs):
            return StorageRecordServiceBlobStorage(blob_storage=blob_storage, project=project, container=container)

        return _build_it

    @staticmethod
    async def build_storage_service_client(host=None, *args, **kwargs) -> StorageRecordServiceClient:
        if host is None:
            host = Config.service_host_storage.value

        return make_storage_record_client(
            host=host,
            timeout=Config.de_client_config_timeout.value,
            max_connections=Config.de_client_config_max_connection.value,
            max_keepalive_connections=Config.de_client_config_max_keepalive.value
        )

    @staticmethod
    async def build_search_service_client(host=None, *args, **kwargs) -> SearchServiceClient:
        if host is None:
            host = Config.service_host_search.value

        return make_search_client(
            host=host,
            timeout=Config.de_client_config_timeout.value,
            max_connections=Config.de_client_config_max_connection.value,
            max_keepalive_connections=Config.de_client_config_max_keepalive.value
        )
