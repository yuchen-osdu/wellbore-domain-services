import uuid
from typing import Optional


class BulkId:
    @staticmethod
    def new_bulk_id() -> str:
        return str(uuid.uuid4())

    @classmethod
    def bulk_urn_encode(cls, bulk_id: str) -> str:
        return uuid.UUID(bulk_id).urn

    @classmethod
    def bulk_urn_decode(cls, urn: str) -> Optional[str]:
        return str(uuid.UUID(urn))
