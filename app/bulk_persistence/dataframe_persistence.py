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

import io

import pandas as pd
from osdu.core.api.storage.blob_storage_base import BlobStorageBase

from app.utils import Context

from .blob_storage import (
    BlobBulk,
    BlobFileExporters,
    create_and_write_blob,
    read_blob,
)
from .bulk_id import BulkId
from .mime_types import MimeTypes
from .tenant_provider import resolve_tenant
from ..helper.traces import with_trace


async def create_and_store_dataframe(ctx: Context, df: pd.DataFrame) -> str:
    """Store bulk on a blob storage"""
    new_bulk_id = BulkId.new_bulk_id()
    tenant = await resolve_tenant(ctx.partition_id)
    async with create_and_write_blob(
        df, file_exporter=BlobFileExporters.PARQUET, blob_id=new_bulk_id
    ) as bulkblob:
        storage: BlobStorageBase = await ctx.app_injector.get(BlobStorageBase)
        await storage.upload(
            tenant,
            bulkblob.id,
            bulkblob.data,
            content_type=bulkblob.content_type,
            metadata=bulkblob.metadata,
        )
        return bulkblob.id


@with_trace('get_dataframe')
async def get_dataframe(ctx: Context, bulk_id: str) -> pd.DataFrame:
    """ fetch bulk from a blob storage, provide column major """
    tenant = await resolve_tenant(ctx.partition_id)
    storage: BlobStorageBase = await ctx.app_injector.get(BlobStorageBase)

    bytes_data = await storage.download(tenant, bulk_id)
    # for now use fix parquet format saving one call
    # meta_data = await storage.download_metadata(tenant.project_id, tenant.bucket_name, bulk_id)
    # content_type = meta_data.metadata["content_type"]
    blob = BlobBulk(
        id=bulk_id,
        data=io.BytesIO(bytes_data),
        content_type=MimeTypes.PARQUET.type,
    )
    data_frame = await read_blob(blob)
    return data_frame
