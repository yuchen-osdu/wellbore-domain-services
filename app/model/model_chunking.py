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

from typing import Optional

from fastapi import Query


class GetDataParams:
    ''' All parameters to query welllog data. '''

    def __init__(
        self,
        offset: Optional[int] = Query(
            default=None,
            ge=0,
            description='The number of rows that are to be skipped and not included in the result.',
            example=5),
        limit: Optional[int] = Query(
            default=None,
            ge=1,
            description='The maximum number of rows to be returned.',
            example=100),
        curves: Optional[str] = Query(
            default=None,
            description='Filters curves. List of curves to be returned.',
            example='MD,GR'),
        describe: Optional[bool] = Query(
            default=False,
            description='The "describe" query option allows clients to request a description of the matching result. '
            '(number of rows, columns name)',
            example='false'),
    ) -> None:
        self.offset = offset
        self.limit = limit
        self.curves = curves
        self.describe = describe
        # orient if json ?
