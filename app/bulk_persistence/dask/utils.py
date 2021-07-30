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
        self.columns = self._get_columns(file_path)  # TODO lazy load
        self.path = file_path

    def _get_columns(self, file_path):
        path, _ = os.path.splitext(file_path)
        with self._fs.open(path + '.meta') as meta_file:
            return json.load(meta_file)['columns']

    def overlap(self, other: 'SessionFileMeta'):
        """Returns True if indexes overlap."""
        return self.end >= other.start and other.end >= self.start

    def has_common_columns(self, other):
        """Returns True if contains common columns with others."""
        return share_items(self.columns, other.columns)


@capture_timings("set_index", handlers=worker_capture_timing_handlers)
def set_index(ddf):  # TODO
    """Set index of the dask dataFrame only if needed."""
    if not ddf.known_divisions or '_idx' not in ddf:
        if '_idx' not in ddf:
            ddf['_idx'] = ddf.index  # we need to create a temporary variable to set it as index
        ddf['_idx'] = ddf['_idx'].astype(ddf.index.dtype)
        return ddf.set_index('_idx', sorted=True)
    return ddf


@capture_timings("do_merge", handlers=worker_capture_timing_handlers)
def do_merge(df1, df2):
    """Combine the 2 dask dataframe. Updates df1 with df2 values if overlap."""
    if df2 is None:
        return df1

    if share_items(df1.columns, df2.columns):
        ddf = df2.combine_first(df1)
    else:
        ddf = df1.join(df2, how='outer')  # join seems faster when there no columns in common

    return ddf[sorted(ddf.columns)]
