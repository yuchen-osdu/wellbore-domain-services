from abc import ABC, abstractmethod
from typing import Iterable, Dict, Optional, Any, Literal
import re

import pandas as pd
from fastapi import status
from pydantic import BaseModel

from .dask.errors import BulkError


class ConsistencyException(BulkError):
    http_status = status.HTTP_400_BAD_REQUEST


class BulkReferenceInfoForConsistency(BaseModel):
    name: str
    start: Any
    end: Any
    monotonic: Optional[Literal["increasing", "decreasing"]]
    hasDuplicate: bool
    hasNan: bool

    @property
    def is_monotonic(self) -> bool:
        return bool(self.monotonic)

    @property
    def is_monotonic_increasing(self) -> bool:
        return self.monotonic == "increasing"

    @property
    def is_monotonic_decreasing(self) -> bool:
        return self.monotonic == "decreasing"

    @classmethod
    def from_series(cls, series: pd.Series) -> "BulkReferenceInfoForConsistency":
        if series.empty:
            # corner case
            return cls(
                name=str(series.name), start=None, end=None, monotonic="increasing", hasDuplicate=False, hasNan=False
            )
        monotonic = None
        if series.is_monotonic_increasing:
            monotonic = "increasing"
        elif series.is_monotonic_decreasing:
            monotonic = "decreasing"

        return cls(
            name=str(series.name),
            start=series.iloc[0],
            end=series.iloc[-1],
            monotonic=monotonic,
            hasDuplicate=not series.is_unique,
            hasNan=series.hasnans,
        )


class BulkInfoForConsistency(BaseModel):
    """gather information from bulk to check the consistency"""

    rowCount: int
    """ number of rows """

    curves: Dict[str, int]
    """ dictionary curve name/id <=> number of column for the curve """

    reference: Optional[BulkReferenceInfoForConsistency]


class DataConsistencyChecks(ABC):
    # regular expression pattern for extracting column name from bulk data column label
    _col_label_pattern = re.compile(r"^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$")

    @classmethod
    @abstractmethod
    async def check_bulk_consistency(cls, record: "Record", bulk_info: BulkInfoForConsistency):
        pass

    @classmethod
    @abstractmethod
    async def check_bulk_consistency_on_commit_session(cls, record: "Record", new_bulk_id):
        pass

    @classmethod
    @abstractmethod
    def check_bulk_consistency_on_post_bulk(cls, record: "Record", df: pd.DataFrame):
        pass

    @staticmethod
    def _get_curve_name_and_column_count(col_labels: Iterable[str]) -> dict:
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
