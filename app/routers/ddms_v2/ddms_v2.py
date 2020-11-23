
from fastapi import APIRouter, Depends, HTTPException
from app.model.model_curated import *
from app.utils import Context
from app.storage.tenant_provider import resolve_tenant


router = APIRouter()


def get_ctx() -> Context:
    return Context.current()



@router.get('/status', response_model=V1AboutResponse,
            summary="Get the status of the service")
async def about(ctx: Context = Depends(get_ctx)) -> V1AboutResponse:
    return V1AboutResponse(user=AboutResponseUser(tenant=ctx.partition_id or 'unknown', email=ctx.user.email))

