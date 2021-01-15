from app.clients import SearchServiceClient
from app.utils import Context


async def get_search_service(ctx: Context) -> SearchServiceClient:
    return await ctx.app_injector.get(SearchServiceClient)
