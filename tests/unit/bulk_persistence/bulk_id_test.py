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

from app.bulk_persistence import BulkId
import uuid


def test_bulk_id_is_an_uuid():
    uuid.UUID(BulkId.new_bulk_id())

# urn decode test
def test_decode_urn_no_prefix():
    uuid, prefix = BulkId.bulk_urn_decode("urn:uuid:489768d2-eee1-4a8f-ae95-7b0c30b0dcd8")
    assert uuid == "489768d2-eee1-4a8f-ae95-7b0c30b0dcd8"
    assert prefix is None

def test_decode_urn_with_prefix():
    uuid, prefix = BulkId.bulk_urn_decode("urn:myprefix:uuid:489768d2-eee1-4a8f-ae95-7b0c30b0dcd8")
    assert uuid == "489768d2-eee1-4a8f-ae95-7b0c30b0dcd8"
    assert prefix == 'myprefix'

def test_decode_urn_none():
    uuid = None
    try:
        uuid, prefix = BulkId.bulk_urn_decode(None)
    except ValueError:
        pass
    assert uuid is None