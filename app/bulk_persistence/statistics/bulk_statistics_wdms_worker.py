from typing import List
from aiohttp import ClientSession
from fastapi import Response

from app.helper.traces import with_trace
from bulk_persistence import BulkURI, MimeTypes


class BulkStatisticWdmsWorker:
    def __init__(self, host: str, http_session: ClientSession):
        self._host = host
        self._http_session = http_session

    @with_trace("worker.compute_statistics")
    async def compute_statistics(self, ctx, record_id: str, bulk_id: str) -> Response:
        headers = {
            "data-partition-id": ctx.partition_id,
            "Authorization": f"Bearer {ctx.auth}",
        }

        async with self._http_session.post(
            f"{self._host}/data/{record_id}/{bulk_id}/statistics",
            headers=headers,
        ) as response:
            return Response(
                content=await response.read(),
                status_code=response.status,
                media_type=MimeTypes.JSON.type,
            )

    @with_trace("worker.get_statistics")
    async def get_statistics(
        self, ctx, record_id: str, bulk_id: str, columns: List[str]
    ) -> Response:
        headers = {
            "data-partition-id": ctx.partition_id,
            "Authorization": f"Bearer {ctx.auth}",
        }

        async with self._http_session.get(
            f"{self._host}/data/{record_id}/{bulk_id}/statistics",
            headers=headers,
            params={"columns": columns},
        ) as response:
            return Response(
                content=await response.read(),
                status_code=response.status,
                media_type=MimeTypes.JSON.type,
            )
