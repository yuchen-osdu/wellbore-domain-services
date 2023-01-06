from typing import Optional
from fastapi import HTTPException, Response
from app.bulk_persistence import GetDataParams, MimeType, JSONOrient
from app.utils import get_http_client_session


async def read_data(host: str,
                    ctx,
                    record_id: str,
                    bulk_id: str,
                    data_param: GetDataParams,
                    accept_type: MimeType,
                    orient: Optional[JSONOrient]) -> Response:
    params = {}
    if data_param.limit:
        params['limit'] = data_param.limit
    if data_param.offset:
        params['offset'] = data_param.offset
    if data_param.curves:
        params['curves'] = data_param.curves
    if data_param.bulk_filter:
        params['filter'] = data_param.bulk_filter
    if orient:
        params['orient'] = orient.value
    if data_param.describe:
        params['describe'] = str(True)

    headers = {
        'accept': accept_type.type,
        'data-partition-id': ctx.partition_id,
        'Authorization': f'Bearer {ctx.auth}'
    }
    http_session = get_http_client_session("wdms_bulk_worker")
    async with http_session.get(
            f'{host}/data/{record_id}/{bulk_id}',
            headers=headers,
            params=params
    ) as resp:
        if resp.status != 200:
            raise HTTPException(status_code=resp.status, detail=await resp.text())
        # TODO have a look to StreamingResponse(content=resp.read(), media_type=accept_type.type)
        return Response(content=await resp.read(), media_type=accept_type.type)
