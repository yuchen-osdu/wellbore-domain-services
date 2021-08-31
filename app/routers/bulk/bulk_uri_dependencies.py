import abc
from abc import ABC
from typing import Optional, Tuple
from fastapi import Request

from app.bulk_persistence import BulkId
from app.model.log_bulk import LogBulkHelper


BULK_URN_PREFIX_VERSION = "wdms-1"
BULK_URI_FIELD = "bulkURI"


class BulkIdAccess(ABC):
    @staticmethod
    @abc.abstractmethod
    def get_bulk_uri(record) -> Tuple[str, Optional[str]]:
        ...

    @staticmethod
    @abc.abstractmethod
    def set_bulk_uri(record, bulk_id):
        ...


class OsduBulkIdAccess(BulkIdAccess):
    @staticmethod
    def get_bulk_uri(record) -> Tuple[str, Optional[str]]:
        bulk_urn = record.data.get("ExtensionProperties", {}).get("wdms", {}).get(BULK_URI_FIELD, None)
        if bulk_urn:
            return BulkId.bulk_urn_decode(bulk_urn)
        return None, None

    @staticmethod
    def set_bulk_uri(record, bulk_id):
        bulk_urn = BulkId.bulk_urn_encode(bulk_id, BULK_URN_PREFIX_VERSION)
        record.data.setdefault("ExtensionProperties", {}).setdefault("wdms", {})[BULK_URI_FIELD] = bulk_urn


class LogBulkIdAccess(BulkIdAccess):
    @staticmethod
    def get_bulk_uri(record, custom_bulk_id_path: Optional[str] = None) -> Tuple[str, Optional[str]]:
        return LogBulkHelper.get_bulk_id(record=record, custom_bulk_id_path=custom_bulk_id_path)

    @staticmethod
    def set_bulk_uri(record, bulk_id: str, custom_bulk_id_path: Optional[str] = None):
        LogBulkHelper.update_bulk_id(
            record=record, bulk_id=bulk_id, prefix=BULK_URN_PREFIX_VERSION, custom_bulk_id_path=custom_bulk_id_path
        )


async def set_log_bulk_id_access(request: Request):
    request.state.bulk_id_access = LogBulkIdAccess


async def set_osdu_bulk_id_access(request: Request):
    request.state.bulk_id_access = OsduBulkIdAccess


def get_bulk_id_access(request: Request) -> BulkIdAccess:
    return request.state.bulk_id_access
