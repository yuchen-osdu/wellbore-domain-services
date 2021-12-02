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

from fastapi import status, HTTPException
from dask.distributed import scheduler
from pyarrow.lib import ArrowException, ArrowInvalid
from functools import wraps

from app.helper.logger import get_logger


class BulkError(Exception):
    http_status: int

    def raise_as_http(self):
        raise HTTPException(status_code=self.http_status, detail=str(self)) from self


class BulkNotFound(BulkError):
    http_status = status.HTTP_404_NOT_FOUND

    def __init__(self, record_id=None, bulk_id=None, message=None):
        ex_message = 'bulk '
        if bulk_id:
            ex_message += f'{bulk_id} '
        if record_id:
            ex_message += f'for record {record_id} '
        ex_message += 'not found'
        if message:
            ex_message += ': ' + message
        super().__init__(ex_message)


class BulkNotProcessable(BulkError):
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, bulk_id=None, message=None):
        ex_message = 'bulk '
        if bulk_id:
            ex_message += f'{bulk_id} '
        ex_message += 'not processable'
        if message:
            ex_message += ': ' + message
        super().__init__(ex_message)


class InternalBulkError(BulkError):
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message=None):
        ex_message = 'Internal bulk error'
        if message:
            ex_message += ': ' + message
        super().__init__(ex_message)


class FilterError(BulkError):
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, reason):
        self.message = f'filter error: {reason}'


def internal_bulk_exceptions(target):
    """
    Decoration to handler exceptions that should be not exposed to outside world. e.g. Pyarrow or Dask exceptions
    """

    @wraps(target)
    async def async_inner(*args, **kwargs):
        try:
            return await target(*args, **kwargs)
        except ArrowInvalid as e:
            get_logger().exception(f"Pyarrow ArrowInvalid when running {target.__name__}")
            raise BulkNotProcessable(f"Unable to process bulk - {str(e)}")
        except ArrowException:
            get_logger().exception(f"Pyarrow exception raised when running {target.__name__}")
            raise BulkNotProcessable("Unable to process bulk - Arrow")
        except scheduler.KilledWorker:
            get_logger().exception(f"Dask worker has been killed when running '{target.__name__}'")
            raise InternalBulkError("Out of memory")
        except Exception:
            get_logger().exception(f"Unexpected exception raised when running '{target.__name__}'")
            raise

    return async_inner
