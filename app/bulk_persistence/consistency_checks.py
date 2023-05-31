from abc import ABC, abstractmethod
from typing import Iterable, Dict, Optional, Any
from enum import Enum
import re

import pandas as pd
from fastapi import status
from pydantic import BaseModel, Field, PrivateAttr
from odes_storage.models import Record

from .dask.errors import BulkError


class ConsistencyException(BulkError):
    http_status = status.HTTP_400_BAD_REQUEST


class Monotonicity(str, Enum):
    Increasing = "increasing"
    Decreasing = "decreasing"


DataframeDictSplit = Dict
"""orient 'split' serialisation, see https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_dict.html"""


class ColumnDescribe(BaseModel):
    """information on a single column"""

    name: str = Field(description="name of the column, if index then set to '_wdms_index_'")
    # TODO see to change start|end to the first|last not NaN value instead
    startEnd: DataframeDictSplit = Field(
        description=(
            "Simplified dataframe contains only the first and last row, with the reference column if requested."
            "See https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_dict.html `split` orient."
            "Dataframe can simply be constructed directly using dataframe constructor as it."
        )
    )
    monotonicity: Optional[Monotonicity] = Field(
        None, description="If not None, data are monotonic increasing or decreasing"
    )
    hasDuplicate: bool = Field(default=False, description="boolean if the column contains any duplicated values")
    hasNan: bool = Field(default=False, description="boolean if there are any NaNs")
    dataType: Optional[str] = Field(default=None, description="dtype of the column, e.g. 'float64'")

    # private attributes
    _start: Any = PrivateAttr(None)
    _end: Any = PrivateAttr(None)

    def __init__(self, **data):
        super().__init__(**data)

        # extract start, end references values
        df = pd.DataFrame(**self.startEnd)
        if df.empty:
            self._start, self._end = None, None
        else:
            if self.dataType:
                # restore type in case values were stringify
                df[self.name] = df[self.name].astype(self.dataType)
            values = df[self.name].tolist()
            if len(values) > 1:
                self._start, self._end = values[0], values[-1]
            else:
                self._start, self._end = values[0], values[0]

    @classmethod
    def from_column(cls, df: pd.DataFrame, reference_name: str) -> "ColumnDescribe":
        if df.empty or reference_name not in df:
            reduced_df = pd.DataFrame()
            column_series = pd.Series()
        else:
            column_series = df[reference_name]
            reduced_df = df.iloc[[0, -1]].copy() if len(df) > 1 else df.copy()
            reduced_df = reduced_df[[reference_name]]

        return cls(
            name=reference_name,
            startEnd=reduced_df.to_dict("split"),
            monotonicity=(
                Monotonicity.Increasing
                if column_series.is_monotonic_increasing
                else Monotonicity.Decreasing if column_series.is_monotonic_decreasing else None
            ),
            hasDuplicate=not column_series.is_unique,
            hasNan=column_series.hasnans,
            dType=str(column_series.dtype),
        )

    @property
    def start(self) -> Any:
        return self._start

    @property
    def end(self) -> Any:
        return self._end

    @property
    def is_monotonic(self) -> bool:
        return self.monotonicity is not None

    @property
    def is_monotonic_increasing(self) -> bool:
        return self.monotonicity == Monotonicity.Increasing

    @property
    def is_monotonic_decreasing(self) -> bool:
        return self.monotonicity == Monotonicity.Decreasing


class BulkInfoForConsistency(BaseModel):
    """gather information from bulk to check the consistency

    class attributes:
        - rowCount: number of rows
        - curves: dictionary curve name/id <=> number of column for the curve
        - reference: column description of the reference if known and provided, the index otherwise
    """

    rowCount: int

    curves: Dict[str, int]

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
