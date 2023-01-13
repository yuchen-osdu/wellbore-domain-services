from typing import Optional
from aiohttp import ClientSession
from fastapi import HTTPException, Response
from .model_chunking import GetDataParams
from .mime_types import MimeType
from .json_orient import JSONOrient
from .bulk_uri import BulkURI


class BulkReaderWdmsWorker:
    def __init__(self, host: str, http_session: ClientSession):
        self._host = host
        self._http_session = http_session

    async def read_data(self,
                        ctx,
                        record_id: str,
                        bulk_uri: BulkURI,
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
        async with self._http_session.get(
                f'{self._host}/data/{record_id}/{bulk_uri.bulk_id}',
                headers=headers,
                params=params
        ) as resp:
            if resp.status != 200:
                # not sure how to properly manage errors yet so directly construct and forward an http exception
                raise HTTPException(status_code=resp.status, detail=await resp.text())

            return Response(content=await resp.read(), media_type=accept_type.type)
