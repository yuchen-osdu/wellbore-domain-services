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

from typing import List, Optional

from pydantic import BaseModel

from odes_storage.models import CreateUpdateRecordsResponse, Record

from app.context import Context, get_ctx
from app.clients.storage_service_client import get_storage_record_service
from app.model.osdu_model import ExtensionProperties_field, ExtensionProperties_WDMS_field, RecordId, RecordVersion


async def fetch_record_dependency(record_id: RecordId, version: Optional[RecordVersion]) -> Record:
    return await fetch_record(get_ctx(), record_id, version)


async def fetch_latest_version_record_dependency(record_id: RecordId) -> Record:
    return await fetch_record(get_ctx(), record_id)


async def fetch_record(ctx: Context,
                       record_id: RecordId,
                       version: Optional[RecordVersion] = None,
                       attribute: List[str] = None) -> Record:
    """
    :param ctx: context
    :param record_id: record identifier
    :param version: log version
    :param attribute: attributes to restrict the returned fields of the record.
    :return: record
    """

    storage_client = await get_storage_record_service(ctx)
    if version:
        return await storage_client.get_record_version(
            id=record_id,
            version=version,
            data_partition_id=ctx.partition_id,
            attribute=attribute
        )
    else:
        return await storage_client.get_record(
            id=record_id,
            data_partition_id=ctx.partition_id,
            attribute=attribute
        )

Attribute_record_wdms_extension_properties = [
    f"data.{ExtensionProperties_field}.{ExtensionProperties_WDMS_field}"
]


async def fetch_record_partial_with_wdms_extension(record_id: RecordId, version: Optional[RecordVersion]) -> Record:
    """ fetch partial record restricting data dict to only ExtensionProperties.wdms """
    record = await fetch_record(get_ctx(), record_id, version, Attribute_record_wdms_extension_properties)

    # let's reconstruct back ExtensionProperties as it in regular record
    # because storage returns it this way:
    #  {
    #   "data": {
    #     "ExtensionProperties.wdms": {
    #       "bulkURI": "urn:wdms-1:uuid:38f0438e-71b8-4806-924b-9753796a77c1"
    #     }
    #   },
    #   "id": ...
    wdms_ext_dict = record.data.pop(f"{ExtensionProperties_field}.{ExtensionProperties_WDMS_field}", {})
    record.data.setdefault(
        ExtensionProperties_field, {}
    ).setdefault(
        ExtensionProperties_WDMS_field, {}
    ).update(wdms_ext_dict)
    return record


async def update_records(ctx: Context, records: List[BaseModel]) -> CreateUpdateRecordsResponse:
    """
    :param ctx: context
    :param records: list of record in dict or pydantic format
    :return: id of the record
    """
    storage_client = await get_storage_record_service(ctx)
    # record_dict_list = [r.dict(exclude_unset=True) if isinstance(r, BaseModel) else r for r in records]
    # just assume it works
    return await storage_client.create_or_update_records(
        record=records, data_partition_id=ctx.partition_id
    )
