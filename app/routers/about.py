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
from app import __version__, __app_name__, __build_number__, __release__
from app.conf import Config
from typing import Dict
from app.auth.auth import require_opendes_authorized_user
from app.routers.common_parameters import response_401, response_403
from app.routers.bulk.bulk_routes_dependencies import BulkIO, get_bulk_io_read, get_bulk_io_write

router = APIRouter()


class AboutResponse(BaseModel):
    service: str = None
    version: str = None
    buildNumber: str = None
    cloudEnvironment: str = None
    release: str = None


@router.get("/about", response_model=AboutResponse, include_in_schema=True)
async def get_about() -> AboutResponse:
    return AboutResponse(
        service=__app_name__,
        version=__version__,
        buildNumber=__build_number__,
        release=__release__,
        cloudEnvironment=Config.cloud_provider.value
    )


class VersionDetailsResponse(BaseModel):
    service: str = None
    version: str = None
    buildNumber: str = None
    release: str = None
    details: Dict[str, str] = None


@router.get("/version", response_model=VersionDetailsResponse, include_in_schema=True,
            responses={**response_401, **response_403})
async def get_version(
        user=Depends(require_opendes_authorized_user, use_cache=False),
        bulk_io_read: BulkIO = Depends(get_bulk_io_read),
        bulk_io_write: BulkIO = Depends(get_bulk_io_write),
):
    # very basic parsing for now
    key_val_list = [key_val.split('=', 1) for key_val in Config.build_details.value.split(';') if '=' in key_val]
    details = {
        key_val[0].strip(): key_val[1].replace('\\"', '"').strip(' "')
        for key_val in key_val_list
    }
    # some additional environment info
    details.update({k: Config.get_env_or_attribute(k).printable_value for k in [
        "environment_name",
        "cloud_provider",
        "de_client_config_timeout",
        "enable_read_fast_track"]}
                   )

    details["read_bulk_backend"] = bulk_io_read.name()
    details["write_bulk_backend"] = bulk_io_write.name()
    if Config.service_host_wdms_worker.value:
        details["enable_wdms_bulk_worker"] = str(True)

    return VersionDetailsResponse(
        service=__app_name__,
        version=__version__,
        buildNumber=__build_number__,
        release=__release__,
        details=details
    )

