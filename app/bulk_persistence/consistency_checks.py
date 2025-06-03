from abc import ABC, abstractmethod
from typing import Iterable, Dict, Optional, Any
from enum import Enum
import re

import pandas as pd
from fastapi import status
from pydantic import BaseModel, Field, PrivateAttr
from odes_storage.models import Record

from .dask.errors import BulkError
from .dask.utils import WDMS_INDEX_NAME
from .dataframe_columns import group_curve_columns


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
    _start_end_df: Any = PrivateAttr(None)

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
        self._start_end_df = df

    # Override equality operator to compare Dataframe field _start_end_df
    def __eq__(self, other):
        if not isinstance(other, ColumnDescribe):
            return NotImplemented

        if isinstance(self._start_end_df, pd.DataFrame) and isinstance(other._start_end_df, pd.DataFrame):
            if not self._start_end_df.equals(other._start_end_df):
                return False
        else:
            if self._start_end_df != other._start_end_df:
                return False

        return (
            self.name == other.name and
            self.monotonicity == other.monotonicity and
            self.hasDuplicate == other.hasDuplicate and
            self.hasNan == other.hasNan and
            self.dataType == other.dataType
        )

    @classmethod
    def from_column(cls, df: pd.DataFrame, reference_name: Optional[str]) -> "ColumnDescribe":
        if df.empty:
            reduced_df = pd.DataFrame()
            column_series = pd.Series()
            reference_name = WDMS_INDEX_NAME
        else:
            if not reference_name or reference_name not in df:
                reference_name = WDMS_INDEX_NAME
            reduced_df = df.iloc[[0, -1]].copy() if len(df) > 1 else df.copy()
            reduced_df[WDMS_INDEX_NAME] = reduced_df.index
            reduced_df = reduced_df[[reference_name]]
            column_series = df[reference_name] if reference_name in df else df.index

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
    def start_end_df(self) -> pd.DataFrame:
        return self._start_end_df

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

    reference: Optional[ColumnDescribe] = None

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, reference_curve: Optional[str] = None) -> "BulkInfoForConsistency":
        curves = {c: len(v) for c, v in group_curve_columns(df.columns).items()}
        return BulkInfoForConsistency(
            rowCount=len(df),
            curves=curves,
            reference=ColumnDescribe.from_column(df, reference_curve)
        )

    # additional properties to ease migration from previous model DataframeBasicDescribe
    @property
    def row_count(self) -> int:
        return self.rowCount

    @property
    def column_count(self) -> int:
        return sum(self.curves.values())

    @property
    def index_start(self) -> str:
        if self.reference is not None and len(self.reference.start_end_df.index):
            return str(self.reference.start_end_df.index[0])
        return ""

    @property
    def index_end(self) -> str:
        if self.reference is not None and len(self.reference.start_end_df.index):
            return str(self.reference.start_end_df.index[-1])
        return ""

    @property
    def index_type(self) -> str:
        if self.reference is not None and len(self.reference.start_end_df.index):
            return str(self.reference.start_end_df.index.dtype)
        return ""


class DataConsistencyChecks(ABC):
    # regular expression pattern for extracting column name from bulk data column label
    _col_label_pattern = re.compile(r"^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$")

    @classmethod
    @abstractmethod
    def get_reference_curve(cls, record: Record) -> Optional[str]:
        pass

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
