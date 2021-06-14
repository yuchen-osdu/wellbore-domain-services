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

from app.utils import Context
from app.clients.storage_service_client import get_storage_record_service

from odes_storage.models import Record




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


