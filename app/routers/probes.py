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

from fastapi import APIRouter
from app.helper.traces import TracingRoute

# Routes require for the liveliness ('/healthz') and readiness ('/healthz') probes for kubernetes
# The root route ('/') is needs for the liveliness of the Google loadbalancer
# which doesn't take into account the ones defined in the yaml deployment file


router = APIRouter(route_class=TracingRoute)


@router.get("/healthz", include_in_schema=False)
async def health():
    return {'status': 'healthy'}


@router.get("/readiness", include_in_schema=False)
async def readiness():
    return {'status': 'healthy'}


@router.get("/", include_in_schema=False)
async def ingress_gce_health():
    return {'status': 'healthy'}
