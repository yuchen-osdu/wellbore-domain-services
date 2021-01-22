from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_az.storage.blob_storage_az import AzureAioBlobStorage
from .app_injector import AppInjector, AppInjectorModule


class AzureInjector(AppInjectorModule):
    def configure(self, app_injector: AppInjector):
        app_injector.register(BlobStorageBase, AzureInjector.build_az_blob_storage)

    @staticmethod
    async def build_az_blob_storage() -> BlobStorageBase:
        return AzureAioBlobStorage()
