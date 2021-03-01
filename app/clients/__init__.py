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

import odes_entitlements
import odes_search
import odes_storage
from odes_entitlements.api_client import AsyncEntitlementsAuthAdministrationApi
from odes_search.api_client import AsyncSearchApi
from odes_storage.api_client import AsyncRecordsApi
from app.conf import Config
from dataclasses import dataclass
from typing import Optional


__all__ = ['EntitlementsAuthServiceClient',
           'SearchServiceClient',
           'StorageRecordServiceClient',
           'make_entitlements_auth_client',
           'make_search_client',
           'make_storage_record_client']

from app.clients.clients_middleware import client_middleware

EntitlementsAuthServiceClient = AsyncEntitlementsAuthAdministrationApi
SearchServiceClient = AsyncSearchApi
StorageRecordServiceClient = AsyncRecordsApi


@dataclass
class Limits:
    max_connections: Optional[int] = None
    max_keepalive_connections: Optional[int] = None
    keepalive_expiry: Optional[float] = 5.0


def make_entitlements_auth_client(host) -> EntitlementsAuthServiceClient:
    entitlements_client = odes_entitlements.ApiClient(
        host=host,
        timeout=Config.de_client_config_timeout.value,
        limits=Limits(
            max_connections=Config.de_client_config_max_connection.value or None,
            max_keepalive_connections=Config.de_client_config_max_keepalive.value or None)
    )

    entitlements_client.add_middleware(middleware=client_middleware)
    return odes_entitlements.AsyncApis(entitlements_client).entitlements_auth_administration_api


def make_search_client(host) -> SearchServiceClient:
    search_client = odes_search.ApiClient(
        host=host,
        timeout=Config.de_client_config_timeout.value,
        limits=Limits(
            max_connections=Config.de_client_config_max_connection.value or None,
            max_keepalive_connections=Config.de_client_config_max_keepalive.value or None)
    )
    search_client.add_middleware(middleware=client_middleware)
    return odes_search.AsyncApis(search_client).search_api


def make_storage_record_client(host) -> StorageRecordServiceClient:
    storage_client = odes_storage.ApiClient(
        host=host,
        timeout=Config.de_client_config_timeout.value,
        limits=Limits(
            max_connections=Config.de_client_config_max_connection.value or None,
            max_keepalive_connections=Config.de_client_config_max_keepalive.value or None)
    )
    storage_client.add_middleware(middleware=client_middleware)
    return odes_storage.AsyncApis(storage_client).records_api
