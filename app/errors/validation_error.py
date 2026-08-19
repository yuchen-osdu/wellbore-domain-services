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

from typing import Union

import jsonschema
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.constants import REF_PREFIX
from fastapi.openapi.utils import validation_error_response_definition, validation_error_definition
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from app.helper.logger import get_logger


async def http422_error_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    """
    Catches and handles pydantic validation errors
    """

    get_logger().exception(f"http422_error_handler - {request.url}")
    return JSONResponse(content=jsonable_encoder({"errors": exc.errors()}), status_code=HTTP_422_UNPROCESSABLE_ENTITY)


async def json_schema_error_handler(
    request: Request, exc: jsonschema.exceptions.ValidationError,
) -> JSONResponse:
    """
    Catches and handles JSon Schema validation errors
    """

    get_logger().exception(f"json_schema_error_handler - {request.url}")
    error_with_location = f"Value of {exc.json_path.lstrip('$.')} is invalid: {exc.message}"
    return JSONResponse(
        content=jsonable_encoder({"errors": error_with_location}), status_code=HTTP_422_UNPROCESSABLE_ENTITY
    )


# TODO remove this once this fastapi issue is closed https://github.com/tiangolo/fastapi/issues/3790
validation_error_definition["properties"] = {
    "loc": {
        "title": "Location", "type": "array", "items": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ]
        }
    },
    "msg": {"title": "Message", "type": "string"},
    "type": {"title": "Error Type", "type": "string"},
}
validation_error_response_definition["properties"] = {
    "errors": {
        "title": "Errors",
        "type": "array",
        "items": {"$ref": "{0}ValidationError".format(REF_PREFIX)},
    },
}
