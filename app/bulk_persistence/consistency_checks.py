from abc import ABC, abstractmethod
from typing import Iterable, Set
import re

import pandas as pd
from fastapi import status

from .dask.errors import BulkError


class ConsistencyException(BulkError):
    http_status = status.HTTP_400_BAD_REQUEST


class DataConsistencyChecks(ABC):
    # regular expression pattern for extracting column name from bulk data column label
    _col_label_pattern = re.compile(r"^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$")

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
                name = m_sel['name']
                array_col[name] = array_col.setdefault(name, 0) + 1
            elif c:
                array_col[c] = 1
        return array_col
