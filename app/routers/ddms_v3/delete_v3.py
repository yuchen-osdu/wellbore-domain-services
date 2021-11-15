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
from typing import List

from fastapi import APIRouter, Depends, Response, status, Body, HTTPException

from app.clients.storage_service_client import get_storage_record_service
from ..common_parameters import REQUIRED_ROLES_READ, REQUIRED_ROLES_WRITE
from app.utils import Context
from app.utils import get_ctx\

router = APIRouter()

@router.post(
    "/records/delete",
    summary="Delete the well. The API performs a logical deletion of the given record. "
            "No recursive delete for OSDU kinds",
    description="{}".format(REQUIRED_ROLES_WRITE),
    operation_id="post_del_multiple_osdu_records",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "record/s not found"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Records deleted successfully"
        },
    },
)
async def post_del_multiple_osdu_records(record_ids: List[str], ctx: Context = Depends(get_ctx)):
    storage_client = await get_storage_record_service(ctx)
    await storage_client.delete_records(
        recordIds=record_ids, data_partition_id=ctx.partition_id
    )
