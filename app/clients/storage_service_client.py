from app.clients import StorageRecordServiceClient
from app.utils import Context


async def get_storage_record_service(ctx: Context) -> StorageRecordServiceClient:
    return await ctx.app_injector.get(StorageRecordServiceClient)
