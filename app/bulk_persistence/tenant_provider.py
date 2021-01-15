from app.conf import Config
from osdu.core.api.storage.tenant import Tenant

async def resolve_tenant(data_partition_id: str) -> Tenant:
    # TODO this is a temporary hardcoded, to be reviewed as we are onboarding different cloud provider
    if Config.cloud_provider.value == 'gcp':
        return Tenant(
            data_partition_id=data_partition_id,
            project_id=Config.default_data_tenant_project_id.value,
            credentials=Config.default_data_tenant_credentials.value,
            bucket_name='logstore-osdu'
        )

    if Config.cloud_provider.value == 'az':
        return Tenant(
            data_partition_id=data_partition_id,
            project_id='',
            bucket_name='wdms-osdu'
        )

    return Tenant(
            data_partition_id=data_partition_id,
            project_id='undefined',
            bucket_name='logstore-osdu'
    )
