import odes_storage
import odes_search
import odes_entitlements
from odes_storage.api_client import AsyncRecordsApi
from odes_search.api_client import AsyncSearchApi
from odes_entitlements.api_client import AsyncEntitlementsAuthAdministrationApi


__all__ = ['EntitlementsAuthServiceClient',
           'SearchServiceClient',
           'StorageRecordServiceClient',
           'make_entitlements_auth_client',
           'make_search_client',
           'make_storage_record_client']

EntitlementsAuthServiceClient = AsyncEntitlementsAuthAdministrationApi
SearchServiceClient = AsyncSearchApi
StorageRecordServiceClient = AsyncRecordsApi


def make_entitlements_auth_client(host, token=None) -> EntitlementsAuthServiceClient:
    return odes_entitlements.AsyncApis(odes_entitlements.AuthApiClient(host=host, token=token)).entitlements_auth_administration_api


def make_search_client(host, token=None) -> SearchServiceClient:
    return odes_search.AsyncApis(odes_search.AuthApiClient(host=host, token=token)).search_api


def make_storage_record_client(host, token=None) -> StorageRecordServiceClient:
    return odes_storage.AsyncApis(odes_storage.AuthApiClient(host=host, token=token)).records_api
