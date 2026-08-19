from typing import Union, AsyncGenerator, Tuple, List, Optional, Any
from uuid import UUID

from httpx import AsyncClient
from fastapi import Response, status

from odes_storage.models import Record

from .sessions_storage import Session
from .errors import BulkWorkerError
from .model_chunking import GetDataParams, DataframeBasicDescribe
from .mime_types import MimeTypes, MimeType
from .json_orient import JSONOrient
from .bulk_uri import BulkURI
from .bulk_io import BulkIO
from .dataframe_validators import DataFrameValidationFunc
from .consistency_checks import DataConsistencyChecks, BulkInfoForConsistency
from app.context import get_headers_from_ctx
from app.helper.traces_ot import get_tracer
_tracer = get_tracer()


class BulkIOWdmsWorker(BulkIO):
    """implementation of bulk I/O using WDMS worker service"""

    def __init__(self, client: AsyncClient):
        self._http_client = client

    def name(self) -> str:
        return "Bulk worker service"

    def close(self):
        self._http_client.aclose()

    @staticmethod
    def _response_as_json(response, expected_status: int = status.HTTP_200_OK) -> Any:
        if response.status_code != expected_status:
            raise BulkWorkerError(response.text, response.status_code)

        return response.json()

    async def write_chunk(
            self,
            ctx,
            data: Union[bytes, AsyncGenerator[bytes, None]],
            content_type: MimeType,
            df_validator_func: DataFrameValidationFunc,
            record_id: str,
            session_id: UUID,
            reference_curve: Optional[str]
    ) -> DataframeBasicDescribe:
        headers = get_headers_from_ctx(ctx)
        headers.update({"Content-Type": content_type.type})

        params = {"reference": reference_curve} if reference_curve else None

        content = await self._prepare_content(data)

        resp = await self._http_client.post(
            f"/data/{record_id}/session/{session_id}", headers=headers, data=content, params=params
        )
        response_obj = self._response_as_json(resp)
        bulk_info = BulkInfoForConsistency(**response_obj)
        return DataframeBasicDescribe(
            rowCount=bulk_info.row_count,
            columnCount=bulk_info.column_count,
            columns=[],
            indexStart=bulk_info.index_start,
            indexEnd=bulk_info.index_end,
            indexType=bulk_info.index_type,
        )

    async def write_complete_session(
            self,
            ctx,
            consistency_checks: DataConsistencyChecks,
            record: Record,
            session: Session,
            update_from_bulk_uri: Optional[BulkURI],
            reference_curve: Optional[str]
    ) -> str:
        headers = get_headers_from_ctx(ctx)

        params = {"completion": session.mode.value}
        if reference_curve:
            params["reference"] = reference_curve
        if update_from_bulk_uri is not None:
            params["from_bulk"] = update_from_bulk_uri.bulk_id

        resp = await self._http_client.patch(
            f"/data/{record.id}/session/{session.id}", headers=headers, params=params
        )
        response_obj = self._response_as_json(resp)
        bulk_id, describe = response_obj["bulkid"], BulkInfoForConsistency(**response_obj["describe"])
        consistency_checks.check_bulk_consistency(record, describe)
        return bulk_id

    @_tracer.start_as_current_span("worker.read_data")
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

        headers = get_headers_from_ctx(ctx)
        headers.update({"accept": accept_type.type})

        resp = await self._http_client.get(
            f"/data/{record_id}/{bulk_uri.bulk_id}", headers=headers, params=params
        )
        if resp.status_code != 200:
            raise BulkWorkerError(resp.text, resp.status_code)

        return Response(content=resp.content, media_type=accept_type.type)

    async def _prepare_content(self, data):
        if isinstance(data, bytes):
            return data
        chunks: List[bytes] = []
        async for chunk in data:
            chunks.append(chunk)
        return b"".join(chunks)

    @_tracer.start_as_current_span("worker.write_data")
    async def write_bulk(
            self,
            ctx,
            data: Union[bytes, AsyncGenerator[bytes, None]],
            content_type: MimeType,
            df_validator_func: DataFrameValidationFunc,
            consistency_checks: DataConsistencyChecks,
            record: Record,
    ) -> Tuple[str, BulkInfoForConsistency]:

        headers = get_headers_from_ctx(ctx)
        headers.update({"Content-Type": content_type.type})

        reference_name = consistency_checks.get_reference_curve(record)
        params = {"reference": reference_name} if reference_name else None

        content = await self._prepare_content(data)

        resp = await self._http_client.post(
            f"/data/{record.id}", headers=headers, data=content, params=params
        )
        response_obj = self._response_as_json(resp)
        bulk_id, describe = response_obj["bulkid"], BulkInfoForConsistency(**response_obj["describe"])
        consistency_checks.check_bulk_consistency(record, describe)
        return bulk_id, describe

    @_tracer.start_as_current_span("worker-get_statistics")
    async def get_statistics(
            self,
            ctx,
            record_id: str,
            bulk_uri: str,
            curves_selection: List[str],
    ) -> Response:

        headers = get_headers_from_ctx(ctx)

        response = await self._http_client.get(
            f"/data/{record_id}/{bulk_uri}/statistics",
            headers=headers,
            params={"curves_selection": curves_selection},
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=MimeTypes.JSON.type,
        )

    @_tracer.start_as_current_span("worker-post_statistics")
    async def post_statistics(
        self,
        ctx,
        record_id: str,
        bulk_uri: str,
        record_version: int,
    ) -> Response:
        """
        Get data from a given record
        :param ctx: context instance
        :param record_id: record id as string
        :param bulk_uri: bulk uri as string
        :param record_version version of given record. Statistics meta-data contains the record's version
        which triggers the statistics computation. But there is no knowledge of OSDU Record inside worker service.
        :return: Return bulk statistics if exist
        """

        headers = get_headers_from_ctx(ctx)

        response = await self._http_client.post(
            f"/data/{record_id}/{bulk_uri}/statistics",
            headers=headers,
            params={"record_version": record_version},
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=MimeTypes.JSON.type,
        )
