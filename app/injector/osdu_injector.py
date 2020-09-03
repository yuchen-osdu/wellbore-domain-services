from app.conf import Config
from app.clients import *
from .app_injector import AppInjector, AppInjectorModule


class OSDUClientsInjector(AppInjectorModule):
    """
    Define the dependencies for wellbore dms osdu
    """
    def __init__(self):
        print('OSDUClientsInjector instantiated')

    def configure(self, injector: AppInjector):
        injector.register(StorageRecordServiceClient, OSDUClientsInjector.build_storage_service_client)
        injector.register(EntitlementsAuthServiceClient, OSDUClientsInjector.build_entitlements_service_client)
        injector.register(SearchServiceClient, OSDUClientsInjector.build_search_service_client)

    @staticmethod
    async def build_storage_service_client(host=None, token=None, *args, **kwargs) -> StorageRecordServiceClient:
        return make_storage_record_client(host or Config.service_host_storage.value, token)

    @staticmethod
    async def build_entitlements_service_client(host=None, token=None, *args, **kwargs) -> EntitlementsAuthServiceClient:
        return make_entitlements_auth_client(host or Config.service_host_entitlements.value, token)

    @staticmethod
    async def build_search_service_client(host=None, token=None, *args, **kwargs) -> SearchServiceClient:
        return make_search_client(host or Config.service_host_search.value, token)
