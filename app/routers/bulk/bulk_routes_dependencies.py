import abc
from abc import ABC
from typing import Optional
from fastapi import Request
from packaging.version import Version

from app.bulk_persistence import BulkURI, BulkIO, BulkIODask, BulkIOWdmsWorker, get_config as get_config_bulk
from app.model.log_bulk import LogBulkHelper
from app.conf import Config
from app.utils import get_http_client_session


BULK_URI_FIELD = "bulkURI"

EARLIEST_KIND_VERSION_INCLUDING_DDMSDATASETS = {
    "WellboreIntervalSet": "1.1.0",
    "WellboreTrajectory": "1.2.0",
    "WellboreMarkerSet": "1.3.0",
    "WellLog": "1.3.0",
}


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
        if hasattr(record, "data") and isinstance(record.data, dict):
            extension_properties = record.data.get("ExtensionProperties", None)
            if extension_properties:
                wdms = extension_properties.get("wdms", None)
                bulk_uri = wdms.get(BULK_URI_FIELD, None) if wdms else None
        elif (
            hasattr(record, "data")
            and hasattr(record.data, "ExtensionProperties")
            and isinstance(record.data.ExtensionProperties, dict)
        ):
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
        OsduBulkIdAccess._set_bulk_uri_ddms_datasets(record, bulk_uri)

    @staticmethod
    def _set_bulk_uri_ddms_datasets(record, bulk_uri: BulkURI):
        kind_parts = record.kind.split("--")
        kind_version = kind_parts[1] if len(kind_parts) == 2 else None
        kind_version_parts = kind_version.split(":") if kind_version and len(kind_version.split(":")) == 2 else None
        if kind_version_parts and kind_version_parts[0] in EARLIEST_KIND_VERSION_INCLUDING_DDMSDATASETS and \
                Version(kind_version_parts[1]) >= Version(EARLIEST_KIND_VERSION_INCLUDING_DDMSDATASETS[kind_version_parts[0]]):
            record.data.setdefault("DDMSDatasets", []).append(bulk_uri.encode_for_ddms_datasets())

class LogBulkIdAccess(BulkIdAccess):
    @staticmethod
    def get_bulk_uri(record, custom_bulk_id_path: Optional[str] = None) -> BulkURI:
        return LogBulkHelper.get_bulk_uri(record=record, custom_bulk_id_path=custom_bulk_id_path)

    @staticmethod
    def set_bulk_uri(record, bulk_id: str):
        LogBulkHelper.update_bulk_uri(record=record, bulk_uri=BulkURI.from_bulk_storage_V1(bulk_id=bulk_id))


async def set_log_bulk_id_access(request: Request):
    request.state.bulk_id_access = LogBulkIdAccess


async def set_osdu_bulk_id_access(request: Request):
    request.state.bulk_id_access = OsduBulkIdAccess


def get_bulk_id_access(request: Request) -> BulkIdAccess:
    if not getattr(request.state, "bulk_id_access", None):
        raise RuntimeError("bulk_id_access dependency is not defined")
    return request.state.bulk_id_access


async def get_bulk_io(is_write_operation: bool = False) -> BulkIO:
    bulk_config = get_config_bulk()
    if (not is_write_operation and bulk_config.dask_enabled_on_read) or (
        is_write_operation and bulk_config.dask_enabled_on_write
    ):
        return BulkIODask(Config.enable_read_fast_track.value)
    return BulkIOWdmsWorker(bulk_config.bulk_worker_host, get_http_client_session("wdms_bulk_worker"))


# still WIP so explicitly distinguish read and write
async def get_bulk_io_read() -> BulkIO:
    return await get_bulk_io(is_write_operation=False)


async def get_bulk_io_write() -> BulkIO:
    return await get_bulk_io(is_write_operation=True)
