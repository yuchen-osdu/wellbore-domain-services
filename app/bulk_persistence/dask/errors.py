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


class BulkError(Exception):
    http_status: int

    def raise_as_http(self):
        raise HTTPException(status_code=self.http_status, detail=str(self))


class BulkNotFound(BulkError):
    http_status = status.HTTP_404_NOT_FOUND

    def __init__(self, record_id, bulk_id):
        self.message = f'bulk {bulk_id} for record {record_id} not found'


class BulkNotProcessable(BulkError):
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, bulk_id):
        self.message = f'bulk {bulk_id} not processable'


class FilterError(BulkError):
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, reason):
        self.message = f'filter error: {reason}'
