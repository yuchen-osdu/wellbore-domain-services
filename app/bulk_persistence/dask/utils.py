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

from itertools import zip_longest
from logging import INFO
from typing import List, Optional

import dask.dataframe as dd
import pandas as pd
import pyarrow.parquet as pa

from app.helper.logger import get_logger
from app.utils import capture_timings


def worker_make_log_captured_timing_handler(level=INFO):
    """log captured timing from the worker subprocess (no access to context)"""

    def log_captured_timing(tag, wall, cpu):
        logger = get_logger()
        if logger:
            logger.log(level, f"Timing of {tag}, wall={wall:.5f}s, cpu={cpu:.5f}s")

    return log_captured_timing


worker_capture_timing_handlers = [worker_make_log_captured_timing_handler(INFO)]


def share_items(seq1, seq2):
    """Returns True if seq1 contains common items with seq2."""
    return not set(seq1).isdisjoint(seq2)


def by_pairs(iterable):
    """Yield successive 2 elements from iterable.
    Fill with None if less than 2 items in iterable."""
    return zip_longest(*[iter(iterable)] * 2, fillvalue=None)


@capture_timings("set_index", handlers=worker_capture_timing_handlers)
def set_index(ddf: dd.DataFrame):
    """Set index of the dask dataFrame only if needed."""
    if not ddf.known_divisions:
        return ddf.set_index(ddf.index, sorted=True)
    return ddf


@capture_timings("join_dataframes", handlers=worker_capture_timing_handlers)
def join_dataframes(dfs: List[dd.DataFrame]):
    if len(dfs) > 1:
        return dfs[0].join(dfs[1:], how='outer')
    return dfs[0] if dfs else None


def rename_index(dataframe: pd.DataFrame, name):
    """Rename the dataframe index"""
    dataframe.index.name = name
    return dataframe


@capture_timings("do_merge", handlers=worker_capture_timing_handlers)
def do_merge(df1: dd.DataFrame, df2: Optional[dd.DataFrame]):
    """Combine the 2 dask dataframe. Updates df1 with df2 values if overlap."""
    if df2 is None:
        return df1

    df1 = set_index(df1)
    df2 = set_index(df2)

    df1 = df1.map_partitions(rename_index, '_wdms_index_')
    df2 = df2.map_partitions(rename_index, '_wdms_index_')

    if share_items(df1.columns, df2.columns):
        return df2.combine_first(df1)
    return df1.join(df2, how='outer')  # join seems faster when there no columns in common


@capture_timings("get_num_rows", handlers=worker_capture_timing_handlers)
def get_num_rows(dataset: pa.ParquetDataset) -> int:
    """Returns the number of rows from a pyarrow ParquetDataset"""
    metadata = dataset.common_metadata
    if metadata and metadata.num_rows > 0:
        return metadata.num_rows
    return sum((piece.get_metadata().num_rows for piece in dataset.pieces))


@capture_timings("index_union", handlers=worker_capture_timing_handlers)
def index_union(idx1: pd.Index, idx2: Optional[pd.Index]):
    """Union of two Index object (check pd.Index.union doc string for more details)"""
    return idx1.union(idx2) if idx2 is not None else idx1
