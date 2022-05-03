from typing import Iterable, NamedTuple, Set, List
from enum import Enum

from .dask.errors import FilterError


class BulkReadFilterOperator(str, Enum):
    Less = 'lt',
    LessOrEqual = 'lte',
    Greater = 'gt',
    GreaterOrEqual = 'gte',
    Equal = 'eq',
    NotEqual = 'neq',
    In = 'in'

    @classmethod
    def from_string(cls, value: str) -> 'BulkReadFilterOperator':
        value = value.lower()
        op = next(filter(lambda e: e.value == value, cls), None)
        if op:
            return op
        raise FilterError('invalid operator: ' + value)

    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class BulkFilter(NamedTuple):
    column: str
    operator: BulkReadFilterOperator
    value: str


class BulkReadFilters:

    def __init__(self, filters: Iterable[BulkFilter]):
        """
        Construct BulkReadFilters and validate inputs
        :param filters: iterable tuple[column, operator, value]
        :throw: FilterError
        return BulkReadFilters object
        """
        column_operators = {}
        self._filters = []
        for column_name, operator, value in filters:
            operators = column_operators.setdefault(column_name, set())
            if operator in operators:
                raise FilterError('Same operator on the same column')
            operators.add(operator)
            self._filters.append(BulkFilter(column_name, operator, value))

        for _, operators in column_operators.items():
            if BulkReadFilterOperator.Equal in operators and BulkReadFilterOperator.In in operators:
                raise FilterError(f"Operator '{BulkReadFilterOperator.Equal}' and '{BulkReadFilterOperator.In}' "
                                  "can't be applied on the same column")

    @property
    def columns(self) -> Set[str]:
        return set((c for c, *_ in self._filters))

    def has_filter(self) -> bool:
        return bool(self._filters)

    def all_filters(self) -> List[BulkFilter]:
        return self._filters
