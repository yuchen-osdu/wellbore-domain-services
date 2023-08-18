import uuid
from unittest.mock import patch

import pytest
from odes_storage.models import Record, Legal, StorageAcl
from app.routers.bulk.bulk_routes_dependencies import (
    OsduBulkIdAccess,
    get_bulk_io_read,
    get_bulk_io_write,
    get_bulk_io,
)
from app.bulk_persistence import BulkIODask, BulkIOWdmsWorker, BulkPersistenceConfig


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
    mock_config = BulkPersistenceConfig()
    mock_config.bulk_worker_host = "mock_host"
    with patch("app.routers.bulk.bulk_routes_dependencies.get_config_bulk", return_value=mock_config):
        # by default
        assert isinstance(await get_bulk_io(True), BulkIODask)
        assert isinstance(await get_bulk_io(False), BulkIODask)
        assert isinstance(await get_bulk_io_write(), BulkIODask)
        assert isinstance(await get_bulk_io_read(), BulkIODask)

        # all worker
        mock_config.dask_enabled_on_read = False
        mock_config.dask_enabled_on_write = False
        inst = await get_bulk_io(True)
        assert isinstance(inst, BulkIOWdmsWorker)
        assert inst._host == "mock_host"
        inst = await get_bulk_io(False)
        assert isinstance(inst, BulkIOWdmsWorker)
        assert inst._host == "mock_host"
        assert isinstance(await get_bulk_io_read(), BulkIOWdmsWorker)
        assert isinstance(await get_bulk_io_write(), BulkIOWdmsWorker)

        mock_config.dask_enabled_on_write = True
        # when is wdms_worker_write_disable return true
        assert isinstance(await get_bulk_io_read(), BulkIOWdmsWorker)
        assert isinstance(await get_bulk_io_write(), BulkIODask)


