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
import jsonschema
from pydantic import ValidationError
from odes_search.exceptions import ApiException as OSDUSearchException
from odes_storage.exceptions import ApiException as OSDUStorageException
from osdu_az.exceptions.data_access_error import DataAccessError as OSDUPartitionException
from odes_schema.exceptions import ApiException as OSDUSchemaException
from starlette import status

from app.routers.bulk.statistics_routes import BulkStatisticsHTTPException, http_stats_error_handler
from app.helper.logger import get_logger
from .unhandled_error import unhandled_error_handler
from .validation_error import http422_error_handler, json_schema_error_handler
from .client_error import (
    http_search_error_handler,
    http_storage_error_handler,
    http_partition_error_handler,
    http_schema_error_handler
)
from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError


async def _log_internal_error_handler(request, exc: HTTPException):
    """
    'decorate' the default fastapi HTTPException handler to log every 500 exception
    """
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger_inst = get_logger()
        if logger_inst is not None:
            logger_inst.exception(f"Internal server error - url: '{request.url}'")
    return await http_exception_handler(request, exc)


def add_exception_handlers(app):
    app.add_exception_handler(BulkStatisticsHTTPException, http_stats_error_handler)
    app.add_exception_handler(RequestValidationError, http422_error_handler)
    app.add_exception_handler(ValidationError, http422_error_handler)
    app.add_exception_handler(OSDUSearchException, http_search_error_handler)
    app.add_exception_handler(OSDUStorageException, http_storage_error_handler)
    app.add_exception_handler(OSDUPartitionException, http_partition_error_handler)
    app.add_exception_handler(OSDUSchemaException, http_schema_error_handler)
    app.add_exception_handler(jsonschema.exceptions.ValidationError, json_schema_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.add_exception_handler(HTTPException, _log_internal_error_handler)
