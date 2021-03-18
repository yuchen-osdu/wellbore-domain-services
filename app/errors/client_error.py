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

import json
from typing import Dict
from odes_search.exceptions import (
    ApiException as OSDUSearchException,
    UnexpectedResponse as OSDUSearchUnexpectedResponse,
    ResponseValidationError as OSDUSearchResponseValidationError,
    ResponseHandlingException as OSDUSearchResponseHandlingException
)
from odes_storage.exceptions import (
    ApiException as OSDUStorageException,
    UnexpectedResponse as OSDUStorageUnexpectedResponse,
    ResponseValidationError as OSDUStorageResponseValidationError,
    ResponseHandlingException as OSDUStorageResponseHandlingException
)

from osdu_az.exceptions.data_access_error import (DataAccessError as OSDUPartitionException)

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from app.utils import get_ctx

OSDU_DATA_ECOSYSTEM_SEARCH = "osdu-data-ecosystem-search"
OSDU_DATA_ECOSYSTEM_STORAGE = "osdu-data-ecosystem-storage"
OSDU_DATA_ECOSYSTEM_PARTITION = "osdu-data-ecosystem-partition"



def load_content(content) -> Dict:
    """
    returns dict from content  whenever content is json or text
    """
    try:
        return json.loads(content)
    except Exception:
        return f"{content}"


async def http_search_error_handler(request: Request, exc: OSDUSearchException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    get_ctx().logger.exception(f"http_search_error_handler - url: '{request.url}'")
    if isinstance(exc, OSDUSearchUnexpectedResponse):
        status = exc.status_code
        errors = [load_content(exc.content)]
    elif isinstance(exc, OSDUSearchResponseValidationError):
        status = exc.status_code
        errors = exc.args
    elif isinstance(exc, OSDUSearchResponseHandlingException):
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.source.args
    else:
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.args

    return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_SEARCH, "errors": errors}, status_code=status)


async def http_storage_error_handler(request: Request, exc: OSDUStorageException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    get_ctx().logger.exception(f"http_storage_error_handler - url: '{request.url}'")
    if isinstance(exc, OSDUStorageUnexpectedResponse) or isinstance(exc, OSDUStorageResponseValidationError):
        status = exc.status_code
        errors = [load_content(exc.content)]
    elif isinstance(exc, OSDUStorageResponseHandlingException):
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.source.args
    else:
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.args

    return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_STORAGE, "errors": errors}, status_code=status)


async def http_partition_error_handler(request: Request, exc: OSDUPartitionException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    get_ctx().logger.exception(f"http_partition_error_handler - url: '{request.url}'")

    return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_PARTITION, "errors": [exc.message]}, 
                        status_code=exc.status_code)
