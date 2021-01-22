from typing import Union

from fastapi.exceptions import RequestValidationError
from fastapi.openapi.constants import REF_PREFIX
from fastapi.openapi.utils import validation_error_response_definition
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
    return JSONResponse({"errors": exc.errors()}, status_code=HTTP_422_UNPROCESSABLE_ENTITY)


validation_error_response_definition["properties"] = {
    "errors": {
        "title": "Errors",
        "type": "array",
        "items": {"$ref": "{0}ValidationError".format(REF_PREFIX)},
    },
}
