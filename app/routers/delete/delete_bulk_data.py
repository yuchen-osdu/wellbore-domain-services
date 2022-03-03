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

from app.bulk_persistence import resolve_tenant
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
import asyncio

from app.bulk_persistence.dask.storage_path_builder import hash_record_id
from app.clients import StorageRecordServiceClient
from app.clients.storage_service_client import get_storage_record_service
from app.routers.bulk.bulk_uri_dependencies import BulkIdAccess

from app.routers.record_utils import fetch_record
from app.context import Context, get_ctx


async def _get_bulk_uri_from_version(ctx: Context, bulk_uri_access: BulkIdAccess, record_id: str, index: int,
                                     record_versions):
    version = record_versions.versions[index]
    record_from_version = await fetch_record(ctx, record_id, version)
    obj_bulk_uri = bulk_uri_access.get_bulk_uri(record=record_from_version)
    if obj_bulk_uri.is_valid():
        return obj_bulk_uri.encode()


async def _get_bulk_uris_of_versions_from_record_id(ctx: Context,
                                                    bulk_uri_access: BulkIdAccess,
                                                    storage_client: StorageRecordServiceClient,
                                                    record_id: str):
    record_versions = await storage_client.get_all_record_versions(id=record_id, data_partition_id=ctx.partition_id)
    record_bulk_uris = [bulk_uri for bulk_uri in await asyncio.gather(*[
        _get_bulk_uri_from_version(ctx, bulk_uri_access, record_id, i, record_versions)
        for i in range(len(record_versions.versions))
    ], return_exceptions=True) if bulk_uri is not None]

    return record_bulk_uris


async def delete_record(
        record_id: str,
        purge: bool,
        ctx: Context,
        bulk_uri_access: BulkIdAccess):
    storage_client = await get_storage_record_service(ctx)

    if not purge:
        await storage_client.delete_record(id=record_id, data_partition_id=ctx.partition_id)
    else:

        record_bulk_uris = await _get_bulk_uris_of_versions_from_record_id(ctx, bulk_uri_access, storage_client,
                                                                           record_id)
        # Delete meta data
        await storage_client.purge_record(id=record_id, data_partition_id=ctx.partition_id)

        tenant = await resolve_tenant(ctx.partition_id)
        blob_storage: BlobStorageBase = await ctx.app_injector.get(BlobStorageBase)
        encode_record_id = hash_record_id(record_id)
        bulk_file_names = await blob_storage.list_objects(tenant=tenant,
                                                          prefix=encode_record_id)

        tasks = [blob_storage.delete(tenant=tenant, object_name=bulk_file_name)
                 for bulk_file_name in bulk_file_names
                 for bulk_id in record_bulk_uris if bulk_id in bulk_file_name]

        for task in tasks:
            # create_task => ensure_future
            delete_result = asyncio.ensure_future(task)
            def task_done(future_result):
                if future_result.exception():
                    get_ctx().logger.exception(
                        f"Exception on bulk versions deletion: {future_result.exception().detail}")

            delete_result.add_done_callback(task_done)
