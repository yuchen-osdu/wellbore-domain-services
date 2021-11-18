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
import pytest

from app.bulk_persistence.bulk_uri import BulkURI
from app.bulk_persistence.bulk_storage_version import (
    BulkStorageVersion_V0, BulkStorageVersion_V1, BulkStorageVersion_Invalid)


# urn decode test
def test_from_uri_without_prefix():
    uri_str = 'urn:uuid:489768d2-eee1-4a8f-ae95-7b0c30b0dcd8'

    bulk_uri = BulkURI.decode(uri_str)
    assert bulk_uri.bulk_id == '489768d2-eee1-4a8f-ae95-7b0c30b0dcd8'
    assert bulk_uri.is_bulk_storage_V0()
    assert bulk_uri.storage_version == BulkStorageVersion_V0
    assert bulk_uri.storage_version.uri_prefix is None
    assert bulk_uri.is_valid()

    # should encode back to the same uri
    assert bulk_uri.encode() == uri_str


def test_decode_urn_with_prefix():
    uri_str = f'urn:{BulkStorageVersion_V1.uri_prefix}:uuid:489768d2-eee1-4a8f-ae95-7b0c30b0dcd8'

    bulk_uri = BulkURI.decode(uri_str)
    assert bulk_uri.bulk_id == '489768d2-eee1-4a8f-ae95-7b0c30b0dcd8'
    assert not bulk_uri.is_bulk_storage_V0()
    assert bulk_uri.storage_version == BulkStorageVersion_V1
    assert bulk_uri.storage_version.uri_prefix == BulkStorageVersion_V1.uri_prefix
    assert bulk_uri.is_valid()

    # should encode back to the same uri
    assert bulk_uri.encode() == uri_str


@pytest.mark.parametrize("bulk_id, version", [
    ('489768d2-eee1-4a8f-ae95-7b0c30b0dcd8', None),
    ('', BulkStorageVersion_Invalid),
    ('489768d2-eee1-4a8f-ae95-7b0c30b0dcd8', BulkStorageVersion_Invalid),
    ('', None),
    ('', BulkStorageVersion_V1),
])
def test_invalid_uri(bulk_id, version):
    invalid_uri = BulkURI(bulk_id, version)
    assert not invalid_uri.is_valid()
    assert not invalid_uri.bulk_id
    assert invalid_uri.storage_version == BulkStorageVersion_Invalid

    # explicit encode raises
    with pytest.raises(ValueError):
        invalid_uri.encode()


def test_decode_urn_invalid_input_should_throw():
    # bad formed urn format
    with pytest.raises(ValueError):
        BulkURI.decode('invalid_urn_uri')

    # bulk_id not a valid UUID
    with pytest.raises(ValueError):
        BulkURI.decode('urn:uuid:invalid_uuid')

    # unknown prefix
    with pytest.raises(ValueError):
        BulkURI.decode('urn:UNKNOWN_PREFIX:uuid:489768d2-eee1-4a8f-ae95-7b0c30b0dcd8')
