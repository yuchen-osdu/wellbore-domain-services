from typing import List
from fastapi import APIRouter, Depends
from app.utils import Context
from app.clients.storage_service_client import get_storage_record_service
from odes_storage.models import *

router = APIRouter()


def get_ctx() -> Context:
    return Context.current()


@router.put('/records', summary='/Create or update a record.')
async def upsert_record(records: List[Record], ctx: Context = Depends(get_ctx)):
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.create_or_update_records(ctx.partition_id, record=records)


@router.get('/records/{record_id}', summary='Gets a record by id.')
async def get_record(record_id: str, ctx: Context = Depends(get_ctx)):
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.get_record(record_id, ctx.partition_id)


@router.delete('/records/{record_id}', summary='Deletes a record by id.')
async def delete_record(record_id: str, ctx: Context = Depends(get_ctx)):
    storage_service = await get_storage_record_service(ctx)
    return await storage_service.delete_record(record_id, data_partition_id=ctx.partition_id)

