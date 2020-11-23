import logging
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from app.utils import get_http_client_session
from osdu_gcp.storage.blob_storage_gcp import GCloudAioStorage
from app.conf import *
from .app_injector import AppInjector, AppInjectorModule
from app.utils import Context
from app.storage.tenant_provider import resolve_tenant

from app.injector.osdu_injector import OSDUClientsInjector
from app.clients import StorageRecordServiceClient
from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage


logger = logging.getLogger('injector')


class MainInjector(AppInjectorModule):
    """
    Gather sub injectors, dependency common to any type of deployment and then overriders.
    """

    def configure(self, app_injector: AppInjector):
        OSDUClientsInjector().configure(app_injector)

        # use gcp storage as file storage whatever deployment is
        app_injector.register(BlobStorageBase, MainInjector.build_gcp_blob_storage)

        # run overriders
        self.overriders(app_injector)

    def overriders(self, app_injector: AppInjector):
        """ defined here any overrider """

        if Config.dev_mode.value:
            storage_path: str = Config.get('USE_INTERNAL_STORAGE_SERVICE_WITH_PATH')
            if storage_path:
                if storage_path.startswith('gs://'):  # use google storage
                    bucket = storage_path.replace('gs://', '').split('/')[0]
                    logger.warning(f'overriding storage service using GCP storage on bucket {bucket} from '
                                   f'project={Config.default_data_tenant_credentials.value}')
                    app_injector.register(StorageRecordServiceClient,
                                          self.make_storage_service_on_gcp_blob_storage_builder(bucket))
                else:
                    logger.warning(f'overriding storage service using localfs blob storage {storage_path}')
                    app_injector.register(StorageRecordServiceClient,
                                          self.make_storage_service_on_localfs_blob_storage_builder(storage_path))

            blob_storage_localfs: str = Config.get('USE_LOCALFS_BLOB_STORAGE_WITH_PATH')
            if blob_storage_localfs:
                async def _blob_storage_builder():
                    return LocalFSBlobStorage(directory=blob_storage_localfs)

                logger.warning(f'overriding blob storage to use local fs on path ' + blob_storage_localfs)
                app_injector.register(BlobStorageBase, _blob_storage_builder)

    @staticmethod
    def make_storage_service_on_gcp_blob_storage_builder(bucket: str):
        """
        create a builder to instantiate a storage service based on GCP storage. It will use the project id set as
        default data tenant and its associated credentials (see Config.default_data_tenant_project_id)
        :param bucket: bucket name
        :return async builder
        """
        return MainInjector.make_storage_service_on_blob_storage_builder(
            GCloudAioStorage(
                session=get_http_client_session(),
                service_account_file=Config.default_data_tenant_credentials.value),
            project=Config.default_data_tenant_project_id.value,
            container=bucket
        )

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
    async def build_gcp_blob_storage(*args, **kwargs) -> BlobStorageBase:
        ctx: Context = Context.current()
        # TODO to be reviewed
        tenant = await resolve_tenant(ctx.partition_id)
        return GCloudAioStorage(
            session=get_http_client_session(),
            service_account_file=tenant.credentials
        )
