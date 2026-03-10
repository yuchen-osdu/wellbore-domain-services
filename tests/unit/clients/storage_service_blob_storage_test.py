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

from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from odes_storage.models import Record


class _FakeBlobStorage:
    def __init__(self):
        self.uploads = []

    async def upload(self, tenant, object_name, data, content_type):
        self.uploads.append((tenant, object_name, data, content_type))


def _minimal_record(record_id: str) -> Record:
    return Record(
        id=record_id,
        kind="osdu:wks:wellbore:1.0.0",
        acl={"viewers": [], "owners": []},
        legal={"legaltags": ["tag"], "otherRelevantDataCountries": ["US"]},
        data={},
    )


@pytest.mark.anyio
async def test_create_or_update_records_uses_each_record_version_for_path():
    storage = _FakeBlobStorage()
    service = StorageRecordServiceBlobStorage(storage, project="proj", container="cont")

    rec1 = _minimal_record("osdu:wks:wellbore:1111111111")
    rec2 = _minimal_record("osdu:wks:wellbore:2222222222")

    await service.create_or_update_records([rec1, rec2], data_partition_id="partition-a")

    uploaded_paths = {obj_name for _, obj_name, _, _ in storage.uploads}
    expected_paths = {
        f"{service._get_record_folder(rec.id, 'partition-a')}/{rec.version}"
        for rec in (rec1, rec2)
    }

    assert uploaded_paths == expected_paths
