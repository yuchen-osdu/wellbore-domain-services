from typing import List, Dict
from fastapi import APIRouter, Depends
from app.utils import Context
from app.clients.search_service_client import get_search_service
from odes_search.models import QueryRequest, QueryResponse
import app.routers.search.search_wrapper as search_wrapper

router = APIRouter()


def get_ctx() -> Context:
    return Context.current()


@router.post('/query/', summary='Query')
async def query(query_request: QueryRequest,
                ctx: Context = Depends(get_ctx)) -> QueryResponse:
    search_service = await get_search_service(ctx)
    return await search_service.query(data_partition_id=ctx.partition_id,
                                      query_request=query_request)


@router.post('/query_with_cursor/', summary='Query with cursor')
async def query(query_request: QueryRequest,
                ctx: Context = Depends(get_ctx)):
    search_service = await get_search_service(ctx)
    return await search_wrapper.SearchWrapper.query_cursorless(
        search_service=search_service,
        data_partition_id=ctx.partition_id,
        query_request=query_request)

