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


@capture_timings("set_index", handlers=worker_capture_timing_handlers)
def set_index(ddf: dd.DataFrame):
    """Set index of the dask dataFrame only if needed."""
    if not ddf.known_divisions:
        return ddf.set_index(ddf.index, sorted=True)
    return ddf


@capture_timings("do_merge", handlers=worker_capture_timing_handlers)
def do_merge(df1: dd.DataFrame, df2: dd.DataFrame):
    """Combine the 2 dask dataframe. Updates df1 with df2 values if overlap."""
    if df2 is None:
        return df1

    df1 = set_index(df1)
    df2 = set_index(df2)
    if share_items(df1.columns, df2.columns):
        ddf = df2.combine_first(df1)
    else:
        ddf = df1.join(df2, how='outer')  # join seems faster when there no columns in common

    return ddf
    
