# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from app.model.log_bulk import LogBulkHelper
from app.bulk_persistence.bulk_uri import BulkURI
from tests.unit.test_utils import basic_record
import uuid
import pytest


@pytest.fixture
def record_with_bulkURI(basic_record):
    basic_record.data = {'custombulkid':'toto', 'log': {'bulkURI': uuid.uuid4().urn}}
    return basic_record


def test_update_bulk_id(record_with_bulkURI):
    b_id = uuid.uuid4()
    b_uri = BulkURI.from_bulk_storage_V0(str(b_id))
    LogBulkHelper.update_bulk_uri(record_with_bulkURI, b_uri)
    assert record_with_bulkURI.data['log']['bulkURI'] == b_id.urn


def test_update_bulk_id_with_path(record_with_bulkURI):
    b_id = uuid.uuid4()
    b_uri = BulkURI.from_bulk_storage_V0(str(b_id))
    LogBulkHelper.update_bulk_uri(record_with_bulkURI, b_uri, "data.custombulkid")
    assert record_with_bulkURI.data['custombulkid'] == b_id.urn


def test_update_bulk_id_on_not_valid_data_should_throw(basic_record):
    basic_record.data = 'not a dict data'

    with pytest.raises(Exception):
        LogBulkHelper.update_bulk_uri(basic_record, BulkURI.from_bulk_storage_V0(str(uuid.uuid4())))


def test_get_update_bulk_id(record_with_bulkURI):
    assert LogBulkHelper.get_bulk_uri(record_with_bulkURI).encode() == record_with_bulkURI.data['log']['bulkURI']


def test_update_bulk_id_on_empty_record(basic_record):
    b_id = uuid.uuid4()
    b_uri = BulkURI.from_bulk_storage_V0(str(b_id))
    LogBulkHelper.update_bulk_uri(basic_record, b_uri)
    assert basic_record.data['log']['bulkURI'] == b_id.urn


def test_get_bulk_id_on_empty_record(basic_record):
    bulk_uri = LogBulkHelper.get_bulk_uri(basic_record)
    assert not bulk_uri.is_valid()
