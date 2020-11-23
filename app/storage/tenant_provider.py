from pydantic import BaseModel
from app.conf import Config


class Tenant(BaseModel):
    data_partition_id: str
    project_id: str
    credentials: str = None
    bucket_name: str


async def resolve_tenant(data_partition_id: str) -> Tenant:
    return Tenant.construct(
        data_partition_id=data_partition_id,
        project_id=Config.default_data_tenant_project_id.value,
        credentials=Config.default_data_tenant_credentials.value,
        bucket_name='logstore-osdu'
    )
