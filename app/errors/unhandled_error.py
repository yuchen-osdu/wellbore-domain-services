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

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    To handle wild exception not caught by other exception handlers
    Logging wild exception is done by TracingMiddleware
    """
    return JSONResponse({"error": [str(exc)]}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
