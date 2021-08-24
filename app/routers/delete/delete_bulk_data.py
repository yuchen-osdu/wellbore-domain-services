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

import asyncio
import json
from typing import List, Optional

import numpy as np
import pandas as pd

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Response,
    status,
    Body
)
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    RecordVersions,
)
from osdu.core.api.storage.tenant import Tenant
from pydantic import BaseModel, Field
from osdu.core.api.storage.blob_storage_base import BlobStorageBase

from app.clients.storage_service_client import get_storage_record_service
from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.routers.bulk.bulk_uri_dependencies import (get_bulk_id_access, BulkIdAccess,
                                                    BULK_URN_PREFIX_VERSION)
from app.routers.bulk.utils import with_dask_blob_storage
from app.routers.common_parameters import json_orient_parameter, REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.routers.delete.persistence import get_bulkURI
from app.routers.record_utils import fetch_record
from app.utils import Context, get_ctx
from app.bulk_persistence.tenant_provider import resolve_tenant


router = APIRouter()

# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------- API delete record ----------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
@router.delete('/record/{id}',
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
        bulk_uri_access: BulkIdAccess = Depends(get_bulk_id_access)):

    storage_client = await get_storage_record_service(ctx)
    if purge:
        record_versions = await storage_client.get_all_record_versions(id=record_id, data_partition_id=ctx.partition_id)
        record_bulk_uris = []
        for i in range(len(record_versions.versions)):
            version = record_versions.versions[i]
            record = await fetch_record(ctx, record_id, version)
            bulk_id, prefix = bulk_uri_access.get_bulk_uri(record=record)
            if bulk_id is not None:
                record_bulk_uris.append(bulk_id)

        print("Delete meta data")
        await storage_client.purge_record(id=record_id, data_partition_id=ctx.partition_id)

        print(record_bulk_uris)

        tenant = await resolve_tenant(ctx.partition_id)
        storage: BlobStorageBase = await ctx.app_injector.get(BlobStorageBase)

        for bulk_id in record_bulk_uris:
            await storage.delete(tenant, bulk_id)

    else:
        await storage_client.delete_record(id=record_id, data_partition_id=ctx.partition_id)
