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

from starlette.requests import Request
from starlette.responses import JSONResponse

from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


OSDU_DATA_ECOSYSTEM_SEARCH = "osdu-data-ecosystem-search"
OSDU_DATA_ECOSYSTEM_STORAGE = "osdu-data-ecosystem-storage"
OSDU_DATA_ECOSYSTEM_ENTITLEMENTS = "osdu-data-ecosystem-entitlements"

CONTENT_ENCODING = "utf-16"


async def http_search_error_handler(_: Request, exc: OSDUSearchException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    if isinstance(exc, OSDUSearchUnexpectedResponse):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_SEARCH, "errors": [exc.reason_phrase]},
                            status_code=exc.status_code)
    elif isinstance(exc, OSDUSearchResponseValidationError):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_SEARCH, "errors": exc.args},
                            status_code=exc.status_code)
    elif isinstance(exc, OSDUSearchResponseHandlingException):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_SEARCH, "errors": exc.source.args},
                            status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_SEARCH, "errors": exc.args},
                            status_code=HTTP_500_INTERNAL_SERVER_ERROR)


async def http_storage_error_handler(_: Request, exc: OSDUStorageException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    if isinstance(exc, OSDUStorageUnexpectedResponse):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_STORAGE, "errors": [exc.reason_phrase]},
                            status_code=exc.status_code)
    elif isinstance(exc, OSDUStorageResponseValidationError):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_STORAGE, "errors": [exc.content]},
                            status_code=exc.status_code)
    elif isinstance(exc, OSDUStorageResponseHandlingException):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_STORAGE, "errors": exc.source.args},
                            status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_STORAGE, "errors": exc.args},
                            status_code=HTTP_500_INTERNAL_SERVER_ERROR)


async def http_entitlements_error_handler(_: Request, exc: OSDUEntitlementsException) -> JSONResponse:
    """
    Catches and handles Exceptions raised by os-python-client
    """
    if isinstance(exc, OSDUEntitlementsUnexpectedResponse):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_ENTITLEMENTS, "errors": [exc.reason_phrase]},
                            status_code=exc.status_code)
    elif isinstance(exc, OSDUEntitlementsResponseValidationError):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_ENTITLEMENTS, "errors": [exc.content]},
                            status_code=exc.status_code)
    elif isinstance(exc, OSDUEntitlementsResponseHandlingException):
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_ENTITLEMENTS, "errors": exc.source.args},
                            status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JSONResponse({"origin": OSDU_DATA_ECOSYSTEM_ENTITLEMENTS, "errors": exc.args},
                            status_code=HTTP_500_INTERNAL_SERVER_ERROR)
