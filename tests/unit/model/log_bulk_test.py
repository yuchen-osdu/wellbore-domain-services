from app.model.log_bulk import LogBulkHelper
from tests.unit.test_utils import basic_record
import uuid
import pytest


@pytest.fixture
def record_with_bulkURI(basic_record):
    basic_record.data = {'log': {'bulkURI': str(uuid.uuid4())}}
    return basic_record


def test_bulk_id_is_an_uuid():
    uuid.UUID(LogBulkHelper.new_bulk_id())


def test_update_bulk_id(record_with_bulkURI):
    record_dict = record_with_bulkURI.dict()
    b_id = str(uuid.uuid4())
    LogBulkHelper.update_bulk_id(record_dict, b_id)
    assert record_dict['data']['log']['bulkURI'] == uuid.UUID(b_id).urn

    LogBulkHelper.update_bulk_id(record_with_bulkURI, b_id)
    assert record_with_bulkURI.data['log']['bulkURI'] == uuid.UUID(b_id).urn


def test_update_bulk_id_on_not_valid_data_should_throw(basic_record):
    basic_record.data = 'not a dict data'

    with pytest.raises(Exception):
        LogBulkHelper.update_bulk_id(basic_record, str(uuid.uuid4()))


def test_get_update_bulk_id(record_with_bulkURI):
    assert LogBulkHelper.get_bulk_id(record_with_bulkURI.dict()) == record_with_bulkURI.data['log']['bulkURI']
    assert LogBulkHelper.get_bulk_id(record_with_bulkURI) == record_with_bulkURI.data['log']['bulkURI']


def test_update_bulk_id_on_empty_record(basic_record):
    b_id = str(uuid.uuid4())
    LogBulkHelper.update_bulk_id(basic_record, b_id)
    assert basic_record.data['log']['bulkURI'] == uuid.UUID(b_id).urn


def test_get_bulk_id_on_empty_record(basic_record):
    assert LogBulkHelper.get_bulk_id(basic_record) is None
    assert LogBulkHelper.get_bulk_id(basic_record.dict()) is None



