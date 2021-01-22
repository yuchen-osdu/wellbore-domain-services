from pydantic import ValidationError
from odes_entitlements.exceptions import ApiException as OSDUEntitlementsException
from odes_search.exceptions import ApiException as OSDUSearchException
from odes_storage.exceptions import ApiException as OSDUStorageException
from osdu_az.exceptions.data_access_error import DataAccessError as OSDUPartitionException

from .unhandled_error import unhandled_error_handler
from .validation_error import http422_error_handler
from .client_error import (
    http_search_error_handler,
    http_storage_error_handler,
    http_entitlements_error_handler,
    http_partition_error_handler
)


__all__ = ['add_exception_handlers']


def add_exception_handlers(app):
    app.add_exception_handler(ValidationError, http422_error_handler)
    app.add_exception_handler(OSDUSearchException, http_search_error_handler)
    app.add_exception_handler(OSDUStorageException, http_storage_error_handler)
    app.add_exception_handler(OSDUEntitlementsException, http_entitlements_error_handler)
    app.add_exception_handler(OSDUPartitionException, http_partition_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
