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

from typing import Optional, List
import re

from fastapi import Query
from pydantic import BaseModel, Field

from .bulk_filter import BulkReadFilterOperator, BulkFilter
from .dask.errors import FilterError


class GetDataParams:
    """ All parameters to query welllog data. """

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
            description='Filters curves. List of curves to be returned. '
                        'The curves are returned in the same order as it is given.',
            example='MD,GR'),
        describe: Optional[bool] = Query(
            default=False,
            description='The "describe" query option allows clients to request a description of the matching result. '
            '(number of rows, columns name)',
            example='false'),
        bulk_filter: Optional[List[str]] = Query(
            default=None,
            alias='filter',
            regex='^(".+"|[^:]+):(' + '|'.join(BulkReadFilterOperator.values()) + '):.*$',
            description="""
The "filter" query parameter allows clients to filter data following the pattern `$column_name:$operator:$value`.
If the column name contains ':', enclose it in double quotation marks (").
<br/>The supported operators are : """ + ', '.join(BulkReadFilterOperator.values()),
            example='MD:lt:1000'
        )
    ) -> None:
        self.offset = offset
        self.limit = limit
        self.curves = curves
        self.describe = describe
        self.bulk_filter = bulk_filter

    def get_curves_list(self) -> List[str]:
        """parse the curves query parameter and return the list of requested curves"""
        if self.curves:
            # split and remove empty
            curves = list(filter(None, map(str.strip, self.curves.split(','))))
            # remove duplicates but maintain order
            return list(dict.fromkeys(curves))
        return []

    re_bulk_filter = re.compile(
        r'^("(?P<enclosed_col>.+)"|(?P<col>[^:]+)):(?P<op>' + '|'.join(BulkReadFilterOperator.values()) + '):(?P<value>.*)$')

    def get_bulk_filters(self) -> List[BulkFilter]:
        """
        returns an iterator over all filters, each iterator provide tuple [column name, operator, value]
        """
        if not self.bulk_filter:
            return []

        result = []
        for f in self.bulk_filter:
            matches = self.re_bulk_filter.match(f)
            if not matches:
                raise FilterError('Invalid filter expression')
            column = matches['col'] or matches['enclosed_col']
            result.append(BulkFilter(column, BulkReadFilterOperator.from_string(matches['op']), matches['value']))
        return result


class DataframeBasicDescribe(BaseModel):
    row_count: int = Field(alias="rowCount")
    column_count: int = Field(alias="columnCount")
    columns: List[str] = Field(
        alias="columns",
        description="list of column. May be truncated if too many columns, then contains the firsts and lasts once")
    index_start: str = Field(alias="indexStart")
    index_end: str = Field(alias="indexEnd")
    index_type: str = Field(alias="indexType")


class DataframeDescribe(BaseModel):
    row_count: int = Field(alias="numberOfRows")
    columns: List[str] = Field(alias="columns", description="list of columns")
