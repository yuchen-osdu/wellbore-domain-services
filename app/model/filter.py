"""
This module groups fonctions to parse the query filter parameters
"""
from contextlib import suppress
from typing import List, Tuple

from app.bulk_persistence.dask.errors import FilterError

FilterOperators = {'lt', 'lte', 'gt', 'gte', 'eq', 'neq', 'in'}


def parse_filter(col_filter: str) -> Tuple[str,str,str]:
    """Parse a column filter expression
    expression should be in the form <column_name>:<operator>:<value>

    >>> parse_filter('A:eq') 
    Exception: Invalid filter expression A:eq
    >>> parse_filter('A:eq:2') 
    ('A', 'eq', '2')
    """
    with suppress(ValueError):
        col, operator, value = col_filter.split(':', maxsplit=2)
        return col, operator, value
    raise FilterError(f'Invalid filter expression {col_filter}')


def get_parsed_filters(bulk_filter: List[str]) -> dict:
    """return the parsed filter query

    >>> get_parsed_filters(['A:lt:2', 'B:lt:2', 'A:gt:3'])
    {'a': {'lt': '2', 'gt': '3'}, 'b': {'lt': '2'}}
    >>> get_parsed_filters(['A'])
    Exception: Invalid filter expression A
    >>> get_parsed_filters(['A:=:2'])
    Exception: Operator = is not supported
    >>> get_parsed_filters(['A:eq:2', 'A:eq:3'])
    Exception: Same operator on the same column
    """
    filter_dict = {}
    for col_name, operator, value in (parse_filter(f) for f in bulk_filter):
        if operator not in FilterOperators:
            raise FilterError(f'Operator {operator} is not supported')
        col_filter = filter_dict.setdefault(col_name, {})
        if operator in col_filter:
            raise FilterError('Same operator on the same column')
        filter_dict[col_name].update({operator: value})
        if all (k in filter_dict[col_name] for k in ("in", "eq")):
            raise FilterError("Operator 'in' and 'eq' can't be applied on the same column")

    return filter_dict
