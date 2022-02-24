import uuid
from odes_storage.models import Record, Legal, StorageAcl
from app.routers.bulk.bulk_uri_dependencies import OsduBulkIdAccess

def test_set_bulk_uri_merge_extension_properties():
    record = Record(id='foo',
                    kind="0",
                    acl=StorageAcl(viewers=[], owners=[]),
                    legal=Legal(),
                    data={})

    record.data = {"ExtensionProperties": {"my_extension_property": 3, "wdms": {"wdms_ext": 4, "bulkURI": 12}}}
    OsduBulkIdAccess.set_bulk_uri(record,  str(uuid.uuid4()))
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