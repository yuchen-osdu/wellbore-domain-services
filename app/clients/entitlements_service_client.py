from app.clients import EntitlementsAuthServiceClient
from app.utils import Context


async def get_entitlements_auth_service(ctx: Context) -> EntitlementsAuthServiceClient:
    return await ctx.app_injector.get(EntitlementsAuthServiceClient, appkey=ctx.app_key, token=ctx.auth)
