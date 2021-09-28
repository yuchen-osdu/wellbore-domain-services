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
import hashlib
import sys

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status)

from app.bulk_persistence import resolve_tenant
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
import asyncio

from app.clients import StorageRecordServiceClient
from app.clients.storage_service_client import get_storage_record_service
from app.helper.traces import with_trace
from app.routers.bulk.bulk_uri_dependencies import (get_bulk_id_access, BulkIdAccess)
from app.routers.bulk.utils import with_dask_blob_storage
from app.routers.common_parameters import REQUIRED_ROLES_WRITE
from app.routers.record_utils import fetch_record
from app.utils import Context, get_ctx
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage

router = APIRouter()


@with_trace('_get_bulk_uri_from_version')
async def _get_bulk_uri_from_version(ctx: Context, bulk_uri_access: BulkIdAccess, record_id: str, index: int,
                                     record_versions):
    version = record_versions.versions[index]
    record_from_version = await fetch_record(ctx, record_id, version)
    bulk_uri, prefix = bulk_uri_access.get_bulk_uri(record=record_from_version)
    return bulk_uri


@with_trace('_get_bulk_uris_of_versions_from_record_id')
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


@router.delete("/record/{record_id}",
               summary="The API performs a logical soft or hard deletion of the given v3 record.",
               description="If 'purge' argument is set to 'true' (HARD Delete): "
                           "It will first find all versions which has bulkURI, "
                           "delete meta data using storage service then bulk data using blob storage service. "
                           "If 'purge' argument is set to 'false' (SOFT Delete): "
                           "It will only delete meta data using storage service."
                           "{}".format(REQUIRED_ROLES_WRITE),
               operation_id="delete_record",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          })
async def delete_record(
        record_id: str,
        purge: bool,
        ctx: Context = Depends(get_ctx),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
        dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage)):
    storage_client = await get_storage_record_service(ctx)

    if not purge:
        return await storage_client.delete_record(id=record_id, data_partition_id=ctx.partition_id)

    record_bulk_uris = await _get_bulk_uris_of_versions_from_record_id(ctx, bulk_uri_access, storage_client,
                                                                       record_id)
    # Delete meta data
    await storage_client.purge_record(id=record_id, data_partition_id=ctx.partition_id)

    tenant = await resolve_tenant(ctx.partition_id)
    blob_storage: BlobStorageBase = await ctx.app_injector.get(BlobStorageBase)
    encode_record_id = dask_blob_storage.encode_record_id(record_id)
    bulk_file_names = await blob_storage.list_objects(tenant=tenant,
                                                 prefix=encode_record_id)

    tasks = [blob_storage.delete(tenant=tenant, object_name=bulk_file_name)
             for bulk_file_name in bulk_file_names
             for bulk_id in record_bulk_uris if bulk_id in bulk_file_name]

    for i in range(len(tasks)):
        # create_task => ensure_future
        delete_result = asyncio.ensure_future(tasks[i])

        def task_done(future_result):
            if future_result.exception() is not None:
                get_ctx().logger.exception(
                    f"Exception on bulk versions deletion: {future_result.exception().detail}")

        delete_result.add_done_callback(task_done)
