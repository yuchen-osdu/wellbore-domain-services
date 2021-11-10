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
import ast
from typing import Optional, List

from fastapi import Query

from app.bulk_persistence.dask.errors import FilterError


class GetDataParams:
    ''' All parameters to query welllog data. '''

    FilterOperators = {'lt', 'lte', 'gt', 'gte', 'eq', 'neq', 'in'}

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
            description='Filters curves. List of curves to be returned. The curves are returned in the same order as it is given.',
            example='MD,GR'),
        describe: Optional[bool] = Query(
            default=False,
            description='The "describe" query option allows clients to request a description of the matching result. '
            '(number of rows, columns name)',
            example='false'),
        bulk_filter: Optional[List[str]] = Query(
            default=None,
            alias='filter',
            description="""
The "filter" query parameter allows clients to filter data following the pattern $column_name:$operator:$value
<br/>supported operation : """ + ','.join(sorted(list(FilterOperators))) + """
<br/>see [website for Filtering API Design](https://www.moesif.com/blog/technical/api-design/REST-API-Design-Filtering-Sorting-and-Pagination/#rhs-colon/).
""",
            example='MD:lt:1000'

    )
    ) -> None:
        self.offset = offset
        self.limit = limit
        self.curves = curves
        self.describe = describe
        self.bulk_filter = bulk_filter
        # orient if json ?

    def get_curves_list(self) -> List[str]:
        """parse the curves query parameter and return the list of requested curves"""
        if self.curves:
            # split and remove empty
            curves = list(filter(None, map(str.strip, self.curves.split(','))))
            # remove duplicates but maintain order
            return list(dict.fromkeys(curves))
        return []

    def get_filters(self) -> dict:
        """return the parsed filter query
        { 
            'col_name_1' : {
                'lt': 10,
                'gt': 50
            },
            'col_name_2': {...}
        }
        """
        if not self.bulk_filter:
            return {}
        filters = {}
        for f in self.bulk_filter:
            col_name, op, *value = f.split(':', maxsplit=2)  # TODO handle exception regular expression
            if op.lower() not in self.FilterOperators:
                raise FilterError(f'Operator {op} does not supported')
            try:
                new_filter = {op: ast.literal_eval(value[0])}
            except:
                new_filter = {op: value[0]}
            if col_name not in filters:
                filters[col_name] = {}
            if op in filters[col_name]:
                raise FilterError('Same operator on the same column')
            filters[col_name].update(new_filter)
        return filters
