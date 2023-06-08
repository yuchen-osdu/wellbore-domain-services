from typing import Union, AsyncGenerator, Tuple, List, Optional
from uuid import UUID

from aiohttp import ClientSession
from fastapi import Response

from odes_storage.models import Record

from .sessions_storage import Session
from .dask.errors import BulkWorkerError
from .model_chunking import GetDataParams
from .mime_types import MimeType
from .json_orient import JSONOrient
from .bulk_uri import BulkURI
from .bulk_io import BulkIO
from .dataframe_validators import DataFrameValidationFunc
from .consistency_checks import DataConsistencyChecks, BulkInfoForConsistency
from app.helper.traces import with_trace


class BulkIOWdmsWorker(BulkIO):
    """implementation of bulk I/O using WDMS worker service"""

    def __init__(self, host: str, http_session: ClientSession):
        self._host = host
        self._http_session = http_session

    async def write_chunk(
        self,
        ctx,
        data: Union[bytes, AsyncGenerator[bytes, None]],
        content_type: MimeType,
        df_validator_func: DataFrameValidationFunc,
        record_id: str,
        session_id: UUID,
    ) -> BulkInfoForConsistency:
        raise NotImplementedError("BulkIOWdmsWorker.write_chunk")

    async def write_complete_session(
        self,
        ctx,
        record: Record,
        session: Session,
        update_from_bulk_uri: Optional[BulkURI],
        consistency_checks: DataConsistencyChecks,
    ) -> str:
        raise NotImplementedError("BulkIOWdmsWorker.write_complete_session")

    @with_trace("worker.read_data")
    async def read_data(
        self,
        ctx,
        record_id: str,
        bulk_uri: BulkURI,
        data_param: GetDataParams,
        accept_type: MimeType,
        orient: Optional[JSONOrient],
    ) -> Response:
        params = {}
        if data_param.limit:
            params["limit"] = data_param.limit
        if data_param.offset:
            params["offset"] = data_param.offset
        if data_param.curves:
            params["curves"] = data_param.curves
        if data_param.bulk_filter:
            params["filter"] = data_param.bulk_filter
        if orient:
            params["orient"] = orient.value
        if data_param.describe:
            params["describe"] = str(True)

        headers = {
            "accept": accept_type.type,
            "data-partition-id": ctx.partition_id,
            "Authorization": f"Bearer {ctx.auth}",
        }
        async with self._http_session.get(
            f"{self._host}/data/{record_id}/{bulk_uri.bulk_id}", headers=headers, params=params
        ) as resp:
            if resp.status != 200:
                raise BulkWorkerError(await resp.text(), resp.status)

            return Response(content=await resp.read(), media_type=accept_type.type)

    async def _prepare_content(self, data):
        if isinstance(data, bytes):
            return data
        chunks: List[bytes] = []
        async for chunk in data:
            chunks.append(chunk)
        return b"".join(chunks)

    @with_trace("worker.read_data")
    async def write_bulk(
        self,
        ctx,
        data: Union[bytes, AsyncGenerator[bytes, None]],
        content_type: MimeType,
        df_validator_func: DataFrameValidationFunc,
        consistency_checks: DataConsistencyChecks,
        record: Record,
    ) -> Tuple[str, BulkInfoForConsistency]:
        headers = {
            "Content-Type": content_type.type,
            "data-partition-id": ctx.partition_id,
            "Authorization": f"Bearer {ctx.auth}",
        }

        reference_name = consistency_checks.get_reference_curve(record)
        params = {"reference": reference_name} if reference_name else None

        content = await self._prepare_content(data)

        async with self._http_session.post(
            f"{self._host}/data/{record.id}", headers=headers, data=content, params=params
        ) as resp:
            if resp.status != 200:
                raise BulkWorkerError(await resp.text(), resp.status)

            response = await resp.json()
            bulk_id, describe = response["bulkid"], BulkInfoForConsistency(**response["describe"])
            consistency_checks.check_bulk_consistency(record, describe)
            return bulk_id, describe
