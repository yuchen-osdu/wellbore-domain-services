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

from fastapi import APIRouter, Depends, HTTPException

from app.model.ddms_model_response import V1AboutResponse, AboutResponseUser
from app.model.model_curated import *
from app.context import Context, get_ctx

router = APIRouter()


@router.get('/status', response_model=V1AboutResponse,
            summary="Get the status of the service")
async def about(ctx: Context = Depends(get_ctx)) -> V1AboutResponse:
    return V1AboutResponse(user=AboutResponseUser(tenant=ctx.partition_id or 'unknown'))

