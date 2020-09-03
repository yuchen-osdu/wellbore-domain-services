from fastapi import APIRouter, Depends
from app.utils import Context
from app.clients.entitlements_service_client import get_entitlements_auth_service
from app.conf import *
import odes_entitlements

router = APIRouter()


def get_ctx() -> Context:
    return Context.current()


@router.get('/auth', summary='Validates the JWT.')
async def auth(ctx: Context = Depends(get_ctx)):
    srv = await get_entitlements_auth_service(ctx)
    await srv.auth()


@router.get('/auth_access_token', summary='Get access token with specified scopes based on authorization token.')
async def auth_access_token(scopes: str, ctx: Context = Depends(get_ctx)):
    srv = await get_entitlements_auth_service(ctx)
    return await srv.auth_access_token(ctx.partition_id, scopes)


@router.get('/groups/', summary='Gets groups.')
async def get_groups(ctx: Context = Depends(get_ctx)):
    client = odes_entitlements.AsyncApis(odes_entitlements.AuthApiClient(
        host=Config.service_host_entitlements.value,
        token=ctx.auth))
    return await client.entitlements_groups_administration_api.groups(ctx.partition_id)
