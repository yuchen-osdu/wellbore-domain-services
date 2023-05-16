from abc import ABC, abstractmethod
from typing import Iterable, Dict, Optional, Any
from enum import Enum
import re

import pandas as pd
from fastapi import status
from pydantic import BaseModel, Field
from odes_storage.models import Record

from .dask.errors import BulkError


class ConsistencyException(BulkError):
    http_status = status.HTTP_400_BAD_REQUEST


class Monotonicity(str, Enum):
    MonotonicIncreasing = "increasing"
    MonotonicDecreasing = "decreasing"


class ColumnDescribe(BaseModel):
    """
    Provide basic description of a column from bulk data. Either constructed locally directly from a dataframe or
    as a response from a remote processing
    """

    name: str = Field(description="column label")
    start: Any = Field(None, description="value at first row")
    end: Any = Field(None, description="value at last row")
    type: Optional[str] = Field(None, description="type of the underlying data")
    monotonicity: Optional[Monotonicity] = Field(
        None, description="If not None, data are monotonic increasing or decreasing"
    )
    hasDuplicate: bool = Field(description="if `False`, data does not contains any duplicated value")
    hasNan: bool = Field(description="if `True`, data contains one or more missing value")

    def __init__(self, **data):
        super().__init__(**data)
        if self.type is not None:
            # in case start, end value has been stringify
            edges = pd.Series([self.start, self.end]).astype(self.type)
            self.start, self.end = edges.iloc[0], edges.iloc[1]

    @property
    def is_monotonic(self) -> bool:
        return self.monotonicity is not None

    @property
    def is_monotonic_increasing(self) -> bool:
        return self.monotonicity == Monotonicity.MonotonicIncreasing

    @property
    def is_monotonic_decreasing(self) -> bool:
        return self.monotonicity == Monotonicity.MonotonicDecreasing

    @classmethod
    def from_series(cls, series: pd.Series) -> "ColumnDescribe":
        if series.empty:
            # corner case, we choose to qualify empty data as monotonic increasing
            return cls(
                name=str(series.name),
                start=None,
                end=None,
                monotonicity=Monotonicity.MonotonicIncreasing,
                hasDuplicate=False,
                hasNan=False,
            )
        monotonic = None
        if series.is_monotonic_increasing:
            monotonic = Monotonicity.MonotonicIncreasing
        elif series.is_monotonic_decreasing:
            monotonic = Monotonicity.MonotonicDecreasing

        return cls(
            name=str(series.name),
            start=series.iloc[0],
            end=series.iloc[-1],
            type=str(series.dtype),
            monotonicity=monotonic,
            hasDuplicate=not series.is_unique,
            hasNan=series.hasnans,
        )


class BulkInfoForConsistency(BaseModel):
    """gather information from bulk to check the consistency"""

    rowCount: int
    """ number of rows """

    curves: Dict[str, int]
    """ dictionary curve name/id <=> number of column for the curve """

    reference: Optional[ColumnDescribe]


class DataConsistencyChecks(ABC):
    # regular expression pattern for extracting column name from bulk data column label
    _col_label_pattern = re.compile(r"^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$")

    @classmethod
    @abstractmethod
    def check_bulk_consistency(cls, record: Record, bulk_info: BulkInfoForConsistency):
        pass

    @classmethod
    @abstractmethod
    async def check_bulk_consistency_on_commit_session(cls, record: Record, new_bulk_id):
        pass

    @classmethod
    @abstractmethod
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        pass

    @staticmethod
    def _get_curve_name_and_column_count(col_labels: Iterable[str]) -> Dict[str, int]:
        """
        Get column names and the number of column from bulk data column labels
        """
        array_col = {}
        for c in col_labels:
            m_sel = DataConsistencyChecks._col_label_pattern.match(c)
            if m_sel:
                name = m_sel["name"]
                array_col[name] = array_col.setdefault(name, 0) + 1
            elif c:
                array_col[c] = 1
        return array_col
