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
            description='Filters curves. List of curves to be returned. The curves are returned in the same order as it is given.',
            example='MD,GR'),
        describe: Optional[bool] = Query(
            default=False,
            description='The "describe" query option allows clients to request a description of the matching result. '
            '(number of rows, columns name)',
            example='false'),
        filter: Optional[List[str]] = Query(
            default=None,
            description='The "filter" query parameter allows clients to filter data following the pattern $colomn_name:$operation:$value.'
            'supported operation : eq, gt, gte, lt, lte',
            exemple='MD:lt:1000'
        )
    ) -> None:
        self.offset = offset
        self.limit = limit
        self.curves = curves
        self.describe = describe
        self.filter = filter
        # orient if json ?

    def get_curves_list(self) -> List[str]:
        """parse the curves query parameter and return the list of requested curves"""
        if self.curves:
            # split and remove emty
            curves = list(filter(None, map(str.strip, self.curves.split(','))))
            # remove duplicates but maintain order
            return list(dict.fromkeys(curves))
        return []

    def get_filters(self) :
        """return the parsed filter query
        { 
            'col_name_1' : {
                'lt': 10,
                'gt': 50
            },
            'col_name_2': {...}
        }
        """
        if not self.filter:
            return {}
        valid_op = {'lt', 'lte', 'gt', 'gte', 'eq'} # TODO should be initialized ones, add other operation like in, startwith, like...
        filters = {}
        for f in self.filter:
            col_name, op, *value = f.split(':')  # TODO handle exception
            if op not in valid_op:
                continue  # TODO raise ?
            new_filter = {op: "".join(value)}
            if col_name not in filters:
                filters[col_name] = {}
            filters[col_name].update(new_filter)
        return filters
