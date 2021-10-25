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

import json
import os
from itertools import zip_longest
from logging import INFO
from typing import List

from app.helper.logger import get_logger
from app.utils import capture_timings

import dask.dataframe as dd


def worker_make_log_captured_timing_handler(level=INFO):
    """log captured timing from the worker subprocess (no access to context)"""
    def log_captured_timing(tag, wall, cpu):
        logger = get_logger()
        if logger:
            logger.log(level, f"Timing of {tag}, wall={wall:.5f}s, cpu={cpu:.5f}s")
    return log_captured_timing


worker_capture_timing_handlers = [worker_make_log_captured_timing_handler(INFO)]

##

def share_items(seq1, seq2):
    """Returns True if seq1 contains common items with seq2."""
    return not set(seq1).isdisjoint(seq2)


def by_pairs(iterable):
    """Yield successive 2 elements from iterable.
    Fill with None if less than 2 items in iterable."""
    return zip_longest(*[iter(iterable)] * 2, fillvalue=None)


class SessionFileMeta:
    def __init__(self, fs, file_path: str) -> None:
        self._fs = fs
        file_name = os.path.basename(file_path)
        start, end, tail = file_name.split('_')
        self.start = float(start)  # data time support ?
        self.end = float(end)
        self.time, self.shape, tail = tail.split('.')
        meta = self._read_meta(file_path)
        self.columns = meta['columns']
        self.dtypes = meta['dtypes']
        self.path = file_path

    def _read_meta(self, file_path):
        path, _ = os.path.splitext(file_path)
        with self._fs.open(path + '.meta') as meta_file:
            return json.load(meta_file)

    def overlap(self, other: 'SessionFileMeta'):
        """Returns True if indexes overlap."""
        return self.end >= other.start and other.end >= self.start

    def has_common_columns(self, other):
        """Returns True if contains common columns with others."""
        return share_items(self.columns, other.columns)


@capture_timings("set_index", handlers=worker_capture_timing_handlers)
def set_index(ddf: dd.DataFrame):
    """Set index of the dask dataFrame only if needed."""
    if not ddf.known_divisions:
        return ddf.set_index(ddf.index, sorted=True).persist()
    return ddf


@capture_timings("join_dataframes", handlers=worker_capture_timing_handlers)
def join_dataframes(dfs: List[dd.DataFrame]):
    if len(dfs) > 1:
        return dfs[0].join(dfs[1:], how='outer')
    return dfs[0] if dfs else None


@capture_timings("do_merge", handlers=worker_capture_timing_handlers)
def do_merge(df1: dd.DataFrame, df2: dd.DataFrame):
    """Combine the 2 dask dataframe. Updates df1 with df2 values if overlap."""
    if df2 is None:
        return df1

    df1 = set_index(df1)
    df2 = set_index(df2)
    if share_items(df1.columns, df2.columns):
        return df2.combine_first(df1)
    return df1.join(df2, how='outer')  # join seems faster when there no columns in common



import re
import numpy as np
re_array_selection = re.compile(r'^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$')

def nesting(df, col):
    values = df[col]
    if not isinstance(df[col].iloc[0], list):
        return df
    nb_rows = len(values)
    nb_col = len(values.iloc[0])
    col_to_nest = []
    for c in df:
        m_sel = re_array_selection.match(c)
        if m_sel and m_sel['name'] == col:
            col_to_nest.append((c, int(m_sel['start'])))

    if not col_to_nest:
        return df

    a = np.array(df[col].explode())
    a = a.reshape(nb_rows, nb_col)
    for c, col_idx in col_to_nest: # TODO sort by index desc ?
        if col_idx >= nb_col:
            empty = np.empty((nb_rows,col_idx-nb_col+1))
            empty[:] = np.NaN
            a = np.hstack((a, empty))
            nb_col = col_idx+1
        a[:,col_idx] = df[c]
        
    df[col] = [r for r in a]
    df = df.drop([c for c, _idx in col_to_nest], axis=1)
    return df

@capture_timings("pack_array", handlers=worker_capture_timing_handlers)
def pack_array(ddf: dd.DataFrame):
    # TODO handle exceptions
    # we should try to detect string vs list columns before calling map_partitions
    for col in ddf.select_dtypes(include=['object']).columns:
        if any(c.startswith(f'{col}[') for c in ddf.columns):
            meta = {c: str(i.dtype) for c, i in ddf.items() if not c.startswith(f'{col}[')} # TODO if col name == A[abc]
            ddf = ddf.map_partitions(nesting, col, meta=meta)
    return ddf
