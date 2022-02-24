import abc
from abc import ABC
from typing import Optional
from fastapi import Request

from app.bulk_persistence.bulk_uri import BulkURI
from app.model.log_bulk import LogBulkHelper


BULK_URI_FIELD = "bulkURI"


class BulkIdAccess(ABC):
    @staticmethod
    @abc.abstractmethod
    def get_bulk_uri(record) -> BulkURI:
        ...

    @staticmethod
    @abc.abstractmethod
    def set_bulk_uri(record, bulk_id: str):
        ...


class OsduBulkIdAccess(BulkIdAccess):
    @staticmethod
    def get_bulk_uri(record) -> BulkURI:
        bulk_uri = None
        if hasattr(record, 'data') and isinstance(record.data, dict):
            extension_properties = record.data.get("ExtensionProperties", None)
            if extension_properties:
                wdms = extension_properties.get("wdms", None)
                bulk_uri = wdms.get(BULK_URI_FIELD, None) if wdms else None
        elif hasattr(record, 'data') and hasattr(record.data, 'ExtensionProperties') and isinstance(record.data.ExtensionProperties, dict):
            wdms = record.data.ExtensionProperties.get("wdms", None)
            bulk_uri = wdms.get(BULK_URI_FIELD, None) if wdms else None
        return BulkURI.decode(bulk_uri)

    @staticmethod
    def set_bulk_uri(record, bulk_id: str):
        if not record.data.get("ExtensionProperties", None):
            record.data["ExtensionProperties"] = {}
        elif not record.data["ExtensionProperties"].get("wdms", None):
            record.data["ExtensionProperties"]["wdms"] = {}
        bulk_uri = BulkURI.from_bulk_storage_V1(bulk_id=bulk_id)
        record.data.setdefault("ExtensionProperties", {}).setdefault("wdms", {})[BULK_URI_FIELD] = bulk_uri.encode()

class LogBulkIdAccess(BulkIdAccess):
    @staticmethod
    def get_bulk_uri(record, custom_bulk_id_path: Optional[str] = None) -> BulkURI:
        return LogBulkHelper.get_bulk_uri(record=record, custom_bulk_id_path=custom_bulk_id_path)

    @staticmethod
    def set_bulk_uri(record, bulk_id: str):
        LogBulkHelper.update_bulk_uri(record=record,
                                      bulk_uri=BulkURI.from_bulk_storage_V1(bulk_id=bulk_id))


async def set_log_bulk_id_access(request: Request):
    request.state.bulk_id_access = LogBulkIdAccess


async def set_osdu_bulk_id_access(request: Request):
    request.state.bulk_id_access = OsduBulkIdAccess


def get_bulk_id_access(request: Request) -> BulkIdAccess:
    return request.state.bulk_id_access
