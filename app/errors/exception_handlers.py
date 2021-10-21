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
from pydantic import ValidationError
from odes_search.exceptions import ApiException as OSDUSearchException
from odes_storage.exceptions import ApiException as OSDUStorageException
from osdu_az.exceptions.data_access_error import DataAccessError as OSDUPartitionException
from starlette import status

from .unhandled_error import unhandled_error_handler
from .validation_error import http422_error_handler
from .client_error import (
    http_search_error_handler,
    http_storage_error_handler,
    http_partition_error_handler
)
from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler

__all__ = ['add_exception_handlers']


def create_custom_http_exception_handler(app, logger):
    """
    overwrite the default fastapi HTTPException handler to log every 500 exception
    https://fastapi.tiangolo.com/tutorial/handling-errors/

    need to register this exception handler in a separate function here and call this function in start up event.
    Because in add_exception_handlers function, we can't get an initialized logger
    """
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request, exc: HTTPException):
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.get_logger().exception(f"Internal server error - url: '{request.url}'")
        return await http_exception_handler(request, exc)


def add_exception_handlers(app):
    app.add_exception_handler(ValidationError, http422_error_handler)
    app.add_exception_handler(OSDUSearchException, http_search_error_handler)
    app.add_exception_handler(OSDUStorageException, http_storage_error_handler)
    app.add_exception_handler(OSDUPartitionException, http_partition_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
