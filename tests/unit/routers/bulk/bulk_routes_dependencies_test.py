import uuid
from unittest.mock import patch

import pytest
from odes_storage.models import Record, Legal, StorageAcl
from packaging.version import Version

from app.routers.bulk.bulk_routes_dependencies import (
    OsduBulkIdAccess,
    get_bulk_io_read,
    get_bulk_io_write,
    get_bulk_io, EARLIEST_KIND_VERSION_INCLUDING_DDMSDATASETS,
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

@pytest.mark.parametrize("kind", [
    "osdu:wks:master-data--Well:1.0.0",
    "osdu:wks:master-data--Well:1.1.0",
    "osdu:wks:master-data--Well:1.2.0",
    "osdu:wks:master-data--Well:1.3.0",
    "osdu:wks:master-data--Wellbore:1.0.0",
    "osdu:wks:master-data--Wellbore:1.1.0",
    "osdu:wks:master-data--Wellbore:1.1.1",
    "osdu:wks:master-data--Wellbore:1.2.0",
    "osdu:wks:master-data--Wellbore:1.3.0",
    "osdu:wks:master-data--Wellbore:1.4.0",
    "osdu:wks:work-product-component--WellboreTrajectory:1.0.0",
    "osdu:wks:work-product-component--WellboreTrajectory:1.1.0",
    "osdu:wks:work-product-component--WellboreTrajectory:1.2.0",
    "osdu:wks:work-product-component--WellboreTrajectory:1.3.0",
    "osdu:wks:work-product-component--WellboreIntervalSet:1.0.0",
    "osdu:wks:work-product-component--WellboreIntervalSet:1.1.0",
    "osdu:wks:work-product-component--WellboreIntervalSet:1.2.0",
    "osdu:wks:work-product-component--WellboreMarkerSet:1.0.0",
    "osdu:wks:work-product-component--WellboreMarkerSet:1.1.0",
    "osdu:wks:work-product-component--WellboreMarkerSet:1.2.0",
    "osdu:wks:work-product-component--WellboreMarkerSet:1.2.1",
    "osdu:wks:work-product-component--WellboreMarkerSet:1.3.0",
    "osdu:wks:work-product-component--WellboreMarkerSet:1.4.0",
    "osdu:wks:work-product-component--WellLog:1.0.0",
    "osdu:wks:work-product-component--WellLog:1.1.0",
    "osdu:wks:work-product-component--WellLog:1.2.0",
    "osdu:wks:work-product-component--WellLog:1.3.0",
    "osdu:wks:work-product-component--WellLog:1.4.0",
    ])
def test_set_bulk_uri_in_ddmsdatasets(kind):
    record = Record(id="foo", kind=kind, acl=StorageAcl(viewers=[], owners=[]), legal=Legal(), data={})
    record.data = {"ExtensionProperties": {"my_extension_property": 3, "wdms": {"wdms_ext": 4, "bulkURI": 12}}}
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    kind_version = kind.split("--")[1].split(":")

    if (kind_version[0] in EARLIEST_KIND_VERSION_INCLUDING_DDMSDATASETS and
            Version(kind_version[1]) >= Version(EARLIEST_KIND_VERSION_INCLUDING_DDMSDATASETS[kind_version[0]])):
        assert "DDMSDatasets" in record.data
    else:
        assert "DDMSDatasets" not in record.data

def test_set_bulk_uri_handles_null_ddmsdatasets():
    """Test that when customer sets DDMSDatasets to null, it gets converted to empty list"""
    record = Record(id="foo", kind="osdu:wks:work-product-component--WellLog:1.3.0", 
                   acl=StorageAcl(viewers=[], owners=[]), legal=Legal(), data={})
    record.data = {
        "ExtensionProperties": {"wdms": {"wdms_ext": 4}},
        "DDMSDatasets": None  # Customer set this to null
    }
    OsduBulkIdAccess.set_bulk_uri(record, str(uuid.uuid4()))
    
    # After setting bulk URI, DDMSDatasets should be an empty list, not None
    assert "DDMSDatasets" in record.data
    assert record.data["DDMSDatasets"] == []
    assert isinstance(record.data["DDMSDatasets"], list)


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


