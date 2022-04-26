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

from fastapi import Depends

from app.context import Context, get_ctx
from app.clients.storage_service_client import get_storage_record_service

from odes_storage.models import (
    CreateUpdateRecordsResponse,
    Record
)
from pydantic import BaseModel


async def fetch_record_dependency(record_id: str, version: int) -> Record:
    return await fetch_record(get_ctx(), record_id, version)


async def fetch_latest_version_record_dependency(record_id: str) -> Record:
    return await fetch_record(get_ctx(), record_id)


async def fetch_record(ctx: Context, record_id: str, version=None) -> Record:
    """
    :param ctx: context
    :param record_id: record identifier
    :param version: log version
    :return: record
    """

    storage_client = await get_storage_record_service(ctx)
    if version:
        return await storage_client.get_record_version(
            id=record_id,
            version=version,
            data_partition_id=ctx.partition_id,
        )
    else:
        return await storage_client.get_record(
            id=record_id,
            data_partition_id=ctx.partition_id,
        )


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
