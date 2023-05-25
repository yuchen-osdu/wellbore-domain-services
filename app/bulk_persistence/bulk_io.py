from typing import Union, AsyncGenerator, Tuple, Optional
from uuid import UUID

from fastapi import Response
from odes_storage.models import Record

from .mime_types import MimeType
from .dataframe_validators import DataFrameValidationFunc
from .consistency_checks import DataConsistencyChecks, BulkInfoForConsistency
from .sessions_storage import Session
from .json_orient import JSONOrient
from .bulk_uri import BulkURI
from .model_chunking import GetDataParams


class BulkIO:
    async def write_bulk(
            self,
            ctx,
            data: Union[bytes, AsyncGenerator[bytes, None]],
            content_type: MimeType,
            df_validator_func: DataFrameValidationFunc,
            consistency_checks: DataConsistencyChecks,
            record: Record,
    ) -> Tuple[str, BulkInfoForConsistency]:
        raise NotImplementedError()

    async def write_chunk(
            self,
            ctx,
            data: Union[bytes, AsyncGenerator[bytes, None]],
            content_type: MimeType,
            df_validator_func: DataFrameValidationFunc,
            record_id: str,
            session_id: UUID,
    ) -> Tuple[str, BulkInfoForConsistency]:
        raise NotImplementedError()

    async def write_complete_session(
            self,
            ctx,
            record: Record,
            session: Session,
            update_from_bulk_uri: Optional[BulkURI],
            consistency_checks: DataConsistencyChecks,
    ) -> str:
        raise NotImplementedError()

    async def read_data(self,
                        ctx,
                        record_id: str,
                        bulk_uri: BulkURI,
                        data_param: GetDataParams,
                        accept_type: MimeType,
                        orient: Optional[JSONOrient]) -> Response:
        raise NotImplementedError()

