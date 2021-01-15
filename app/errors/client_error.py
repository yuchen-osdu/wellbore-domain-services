from odes_entitlements.exceptions import (
    ApiException as OSDUEntitlementsException,
    UnexpectedResponse as OSDUEntitlementsUnexpectedResponse,
    ResponseValidationError as OSDUEntitlementsResponseValidationError,
    ResponseHandlingException as OSDUEntitlementsResponseHandlingException
)
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
OSDU_DATA_ECOSYSTEM_ENTITLEMENTS = "osdu-data-ecosystem-entitlements"
OSDU_DATA_ECOSYSTEM_PARTITION = "osdu-data-ecosystem-partition"

CONTENT_ENCODING = "utf-16"


async def http_search_error_handler(request: Request, exc: OSDUSearchException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    get_ctx().logger.exception(f"http_search_error_handler - url: '{request.url}'")
    if isinstance(exc, OSDUSearchUnexpectedResponse):
        status = exc.status_code
        errors = [exc.reason_phrase]
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
    if isinstance(exc, OSDUStorageUnexpectedResponse):
        status = exc.status_code
        errors = [exc.reason_phrase]
    elif isinstance(exc, OSDUStorageResponseValidationError):
        status = exc.status_code
        errors = [exc.content]
    elif isinstance(exc, OSDUStorageResponseHandlingException):
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.source.args
    else:
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.args

    return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_STORAGE, "errors": errors}, status_code=status)


async def http_entitlements_error_handler(request: Request, exc: OSDUEntitlementsException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    get_ctx().logger.exception(f"http_entitlements_error_handler - url: '{request.url}'")
    if isinstance(exc, OSDUEntitlementsUnexpectedResponse):
        status = exc.status_code
        errors = [exc.reason_phrase]
    elif isinstance(exc, OSDUEntitlementsResponseValidationError):
        status = exc.status_code
        errors = [exc.content]
    elif isinstance(exc, OSDUEntitlementsResponseHandlingException):
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.source.args
    else:
        status = HTTP_500_INTERNAL_SERVER_ERROR
        errors = exc.args

    return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_ENTITLEMENTS, "errors": errors}, status_code=status)


async def http_partition_error_handler(request: Request, exc: OSDUPartitionException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    get_ctx().logger.exception(f"http_partition_error_handler - url: '{request.url}'")

    return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_PARTITION, "errors": [exc.message]}, 
                        status_code=exc.status_code)
