import uuid
from unittest.mock import patch

import pytest
from odes_storage.models import Record, Legal, StorageAcl
from app.routers.bulk.bulk_routes_dependencies import (
    OsduBulkIdAccess,
    get_bulk_io_read,
    get_bulk_io_write_no_session,
    get_bulk_io_write_with_session,
    get_bulk_io,
)
from app.bulk_persistence import BulkIODask, BulkIOWdmsWorker


def test_set_bulk_uri_merge_extension_properties():
    record = Record(id="foo", kind="0", acl=StorageAcl(viewers=[], owners=[]), legal=Legal(), data={})

    record.data = {"ExtensionProperties": {"my_extension_property": 3, "wdms": {"wdms_ext": 4, "bulkURI": 12}}}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    assert record.data["ExtensionProperties"]["my_extension_property"] == 3
    assert record.data["ExtensionProperties"]["wdms"]["wdms_ext"] == 4
    assert record.data["ExtensionProperties"]["wdms"]["bulkURI"] != 12

    record.data = {"ExtensionProperties": {"my_extension_property": 3, "wdms": {"wdms_ext": 4}}}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    assert record.data["ExtensionProperties"]["my_extension_property"] == 3
    assert record.data["ExtensionProperties"]["wdms"]["wdms_ext"] == 4
    assert "bulkURI" in record.data["ExtensionProperties"]["wdms"]

    record.data = {"ExtensionProperties": {"my_extension_property": 3}}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    assert record.data["ExtensionProperties"]["my_extension_property"] == 3
    assert "wdms" in record.data["ExtensionProperties"]
    assert "bulkURI" in record.data["ExtensionProperties"]["wdms"]

    record.data = {"ExtensionProperties": {}}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    assert "wdms" in record.data["ExtensionProperties"]
    assert "bulkURI" in record.data["ExtensionProperties"]["wdms"]

    record.data = {}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    assert "wdms" in record.data["ExtensionProperties"]
    assert "bulkURI" in record.data["ExtensionProperties"]["wdms"]

    record.data = {"ExtensionProperties": None}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    assert "wdms" in record.data["ExtensionProperties"]
    assert "bulkURI" in record.data["ExtensionProperties"]["wdms"]

    record.data = {"ExtensionProperties": {"wdms": None}}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    assert "wdms" in record.data["ExtensionProperties"]
    assert "bulkURI" in record.data["ExtensionProperties"]["wdms"]


@pytest.mark.anyio
async def test_get_bulk_io_dependency():
    with patch("app.routers.bulk.bulk_routes_dependencies.bulk_worker_host", return_value="mock_host"):
        inst = await get_bulk_io()
        assert isinstance(inst, BulkIOWdmsWorker)
        assert inst._host == "mock_host"
        assert isinstance(await get_bulk_io_read(), BulkIOWdmsWorker)
        assert isinstance(await get_bulk_io_write_no_session(), BulkIOWdmsWorker)
        assert isinstance(await get_bulk_io_write_with_session(), BulkIOWdmsWorker)

    with patch("app.routers.bulk.bulk_routes_dependencies.bulk_worker_host", return_value=None):
        assert isinstance(await get_bulk_io(), BulkIODask)
        assert isinstance(await get_bulk_io_write_no_session(), BulkIODask)
        assert isinstance(await get_bulk_io_read(), BulkIODask)
        assert isinstance(await get_bulk_io_write_with_session(), BulkIODask)

    # by default
    assert isinstance(await get_bulk_io(), BulkIODask)
    assert isinstance(await get_bulk_io_write_no_session(), BulkIODask)
    assert isinstance(await get_bulk_io_read(), BulkIODask)
    assert isinstance(await get_bulk_io_write_with_session(), BulkIODask)
