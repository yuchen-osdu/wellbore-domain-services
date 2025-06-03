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

from typing import ClassVar
import re

from pydantic import BaseModel, Field, field_validator

from .bulk_filter import BulkReadFilterOperator, BulkFilter
from .dask.errors import FilterError

CURVES_EXAMPLES = {
    "all": {
        "summary": "Select all curves",
        "value": ""
    },
    "basic": {
        "summary": "Select specific curves",
        "value": "MD,GR"
    },
    "array-slice": {
        "summary": "Select a slice of array curves",
        "value": "ARR[10:50]"
    },
    "array-curve": {
        "summary": "Select one specific curve of an array",
        "value": "ARR[100]"
    },
    "array-slice-plus-curve": {
        "summary": "Select slice of array + another curve(s)",
        "value": "MD,ARR[50:55],GR"
    },
}

BULK_FILTER_DESCRIPTION = f"""

The "filter" query parameter allows clients to filter by rows, it selects rows data following the pattern `$column_name:$operator:$value`.  
The supported operators are : {', '.join(BulkReadFilterOperator.values())}.  

Note: If the column name contains ':', enclose it in double quotation marks (").
"""


BULK_FILTER_EXAMPLES = {
    "simple-md-filter": {
        "summary": "Select rows when column 'MD' values >= 1000",
        "value": ["MD:gte:1000"]
    },
    "simple-md-filter-2": {
        "summary": "Select rows when 'MD' column values <= 1000",
        "value": ["MD:lte:1000"]
    },
    "double-md-filter": {
        "summary": "Select 'MD' > 1000 and 'MD' < 42000",
        "value": ["MD:gt:1000", "MD:lt:42000"]
    },
}

BULK_FILTER_PATTERN = r'^(".+"|[^:]+):(' + '|'.join(BulkReadFilterOperator.values()) + '):.*$'


class GetDataParams(BaseModel):
    """All parameters to query welllog data."""

    offset: int | None = Field(
        default=None,
        ge=0,
        description="The number of rows that are to be skipped and not included in the result.",
        examples=[5]
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        description="The maximum number of rows to be returned.",
        examples=[100]
    )
    curves: str | None = Field(
        default=None,
        description="Filters curves. List of curves to be returned. "
                    "The curves are returned in the same order as it is given.",
        examples=[CURVES_EXAMPLES]
    )
    describe: bool | None = Field(
        default=False,
        description="The 'describe' query option allows clients to request a description of the matching result. "
                    "(number of rows, columns name)",
        examples=["false"]
    )
    bulk_filter: list[str] | None = Field(
        default=None,
        alias="filter",
        description=BULK_FILTER_DESCRIPTION,
        examples=[BULK_FILTER_EXAMPLES]
    )

    re_bulk_filter: ClassVar[re.Pattern] = re.compile(
        r'^("(?P<enclosed_col>.+)"|(?P<col>[^:]+)):(?P<op>' + '|'.join(BulkReadFilterOperator.values()) + '):(?P<value>.*)$')

    @classmethod
    @field_validator("bulk_filter", mode="before")
    def validate_bulk_filter(cls, filters):
        if filters is None:
            return None
        pattern = BULK_FILTER_PATTERN
        for filter_str in filters:
            if not re.match(pattern, filter_str):
                raise ValueError(f"Invalid filter expression: {filter_str}")
        return filters

    def get_curves_list(self) -> list[str]:
        """parse the curves query parameter and return the list of requested curves"""
        if self.curves:
            # split and remove empty
            curves = list(filter(None, map(str.strip, self.curves.split(','))))
            # remove duplicates but maintain order
            return list(dict.fromkeys(curves))
        return []

    def get_bulk_filters(self) -> list[BulkFilter]:
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
    # TODO to remove, to be replaced by new df description model

    row_count: int = Field(alias="rowCount")
    column_count: int = Field(alias="columnCount")
    columns: list[str] = Field(
        alias="columns",
        description="list of column. May be truncated if too many columns, then contains the firsts and lasts once")
    index_start: str = Field(alias="indexStart")
    index_end: str = Field(alias="indexEnd")
    index_type: str = Field(alias="indexType")


class DataframeDescribe(BaseModel):
    numberOfRows: int = Field(description="total number of rows")
    columns: list[str] = Field(description="list of columns")
