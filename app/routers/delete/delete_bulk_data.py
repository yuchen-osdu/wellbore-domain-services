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
import sys

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status
)

from osdu.core.api.storage.blob_storage_base import BlobStorageBase

from app.clients import StorageRecordServiceClient
from app.clients.storage_service_client import get_storage_record_service
from app.routers.bulk.bulk_uri_dependencies import (get_bulk_id_access, BulkIdAccess)
from app.routers.bulk.utils import with_dask_blob_storage
from app.routers.common_parameters import REQUIRED_ROLES_WRITE
from app.routers.record_utils import fetch_record
from app.utils import Context, get_ctx
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage

router = APIRouter()


async def _get_bulk_uris_of_versions_from_record_id(ctx: Context,
                                              bulk_uri_access: BulkIdAccess,
                                              storage_client: StorageRecordServiceClient,
                                              record_id: str):
    record_versions = await storage_client.get_all_record_versions(id=record_id, data_partition_id=ctx.partition_id)
    record_bulk_uris = []
    for i in range(len(record_versions.versions)):
        version = record_versions.versions[i]
        record_from_version = await fetch_record(ctx, record_id, version)
        bulk_uri, prefix = bulk_uri_access.get_bulk_uri(record=record_from_version)
        if bulk_uri is not None:
            record_bulk_uris.append(bulk_uri)
    return record_bulk_uris


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------- API delete record ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.delete("/record/{record_id}",
               summary="The API performs a logical deletion of the given record",
               description="{}".format(REQUIRED_ROLES_WRITE),
               operation_id="del_purge",
               status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response,
               responses={status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
                          status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"}
                          })
async def delete_purge_record(
        record_id: str,
        purge: bool,
        ctx: Context = Depends(get_ctx),
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access),
        dask_blob_storage: DaskBulkStorage = Depends(with_dask_blob_storage)):
    storage_client = await get_storage_record_service(ctx)

    if purge:
        record_bulk_uris = await _get_bulk_uris_of_versions_from_record_id(ctx, bulk_uri_access, storage_client, record_id)

        # Delete meta data
        await storage_client.purge_record(id=record_id, data_partition_id=ctx.partition_id)

        # Get bulk_ids directly from storage to check if it's match
        # with the number of bulk uris retrieved from record version
        bulk_ids = dask_blob_storage.get_bulk_ids(record_id)

        # In tiny cases record_id sha1 can be similar with a other record_id sha1
        # To delete only data relative to the record_id wanted, we deleting data by version instead of the entire folder
        if len(record_bulk_uris) == len(bulk_ids):
            dask_blob_storage.delete_entity(record_id)
        else:
            for bulk_id in record_bulk_uris:
                dask_blob_storage.delete_bulk(record_id=record_id, bulk_id=bulk_id)
    else:
        await storage_client.delete_record(id=record_id, data_partition_id=ctx.partition_id)
