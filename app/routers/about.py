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

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app import __version__, __app_name__, __build_number__
from app.conf import Config
from typing import Dict
from app.auth.auth import require_opendes_authorized_user
from app.routers.common_parameters import response_401, response_403

router = APIRouter()

class AboutResponse(BaseModel):
    service: str = None
    version: str = None
    buildNumber: str = None
    cloudEnvironment: str = None


@router.get("/about", response_model=AboutResponse, include_in_schema=True)
async def get_about() -> AboutResponse:
    return AboutResponse.construct(
        service=__app_name__,
        version=__version__,
        buildNumber=__build_number__,
        cloudEnvironment=Config.cloud_provider.value
    )


class VersionDetailsResponse(BaseModel):
    service: str = None
    version: str = None
    buildNumber: str = None
    details: Dict[str, str] = None


@router.get("/version", response_model=VersionDetailsResponse, include_in_schema=True,
            responses={**response_401, **response_403})
async def get_version(user=Depends(require_opendes_authorized_user, use_cache=False)):
    # very basic parsing for now
    key_val_list = [key_val.split('=', 1) for key_val in Config.build_details.value.split(';') if '=' in key_val]
    details = {
        key_val[0].strip(): key_val[1].replace('\\"', '"').strip(' "')
        for key_val in key_val_list
    }
    # codecs.decode(s, 'unicode_escape')
    return VersionDetailsResponse.construct(
        service=__app_name__,
        version=__version__,
        buildNumber=__build_number__,
        details=details
    )

