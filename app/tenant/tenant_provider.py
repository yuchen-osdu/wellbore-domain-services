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

from app.conf import Config
from osdu.core.api.storage.tenant import Tenant

async def resolve_tenant(data_partition_id: str) -> Tenant:
    # TODO this is a temporary hardcoded, to be reviewed as we are onboarding different cloud provider
    if Config.cloud_provider.value == 'gc':
        return Tenant(
            data_partition_id=data_partition_id,
            project_id=Config.default_data_tenant_project_id.value,
            credentials=Config.default_data_tenant_credentials.value,
            bucket_name=f'{Config.default_data_tenant_project_id.value}-logstore-osdu'
        )

    if Config.cloud_provider.value == 'az':
        return Tenant(
            data_partition_id=data_partition_id,
            project_id='',
            bucket_name=Config.az_bulk_container
        )

    if Config.cloud_provider.value == 'ibm':
        return Tenant(
            data_partition_id=data_partition_id,
            project_id=Config.default_data_tenant_project_id.value,
            bucket_name='logstore-osdu-ibm'
        )

    if Config.cloud_provider.value == 'aws':
        return Tenant(
            data_partition_id=data_partition_id,
            project_id='',
            bucket_name=f'{data_partition_id}-logstore-osdu' #folder name
        )
    return Tenant(
            data_partition_id=data_partition_id,
            project_id='undefined',
            bucket_name='logstore-osdu'
    )
