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

import hashlib
import json
import os
import time
from typing import List

import pandas as pd
from app.bulk_persistence.dask.utils import share_items


class SessionFileMeta:
    """The class extract information about chunks."""

    def __init__(self, fs, file_path: str) -> None:
        self._fs = fs
        file_name = os.path.basename(file_path)
        start, end, tail = file_name.split('_')
        self.start = float(start)  # data time support ?
        self.end = float(end)
        self.time, self.shape, tail = tail.split('.')
        self._meta = None
        self.path = file_path

    def _read_meta(self):
        if not self._meta:
            path, _ = os.path.splitext(self.path)
            with self._fs.open(path + '.meta') as meta_file:
                self._meta = json.load(meta_file)
        return self._meta

    @property
    def columns(self) -> List[str]:
        """Return the column names"""
        return self._read_meta()['columns']

    @property
    def dtypes(self) -> List[str]:
        """Return the column dtypes"""
        return self._read_meta()['dtypes']

    @property
    def nb_rows(self) -> int:
        """Retrun the number of rows of the chunk"""
        return self._read_meta()['nb_rows']

    @property
    def index_hash(self) -> str:
        """Retrun the index hash"""
        return self._read_meta()['index_hash']

    def overlap(self, other: 'SessionFileMeta') -> bool:
        """Returns True if indexes overlap."""
        return self.end >= other.start and other.end >= self.start

    def has_common_columns(self, other: 'SessionFileMeta') -> bool:
        """Returns True if contains common columns with others."""
        return share_items(self.columns, other.columns)


def generate_chunk_filename(dataframe: pd.DataFrame) -> str:
    """Generate a chunk filename composed of information from the given dataframe
    {first_index}_{last_index}_{time}.{shape}
    The shape is a hash of columns names + columns dtypes
    If chunks have same shape, dask can read them together.

    Warnings:
        - This funtion is not idempotent !
        - Do not modify the name without updating the class SessionFileMeta !
          Indeed, SessionFileMeta parse information from the chunk filename
        - Filenames impacts partitions order in Dask as it order them by 'natural key'
          Thats why the start index is in the first position

    Raises:
        IndexError - if empty dataframe

    >>> generate_chunk_filename(pd.DataFrame({'A': range(10), 'B': range(10)}, index=range(10)))
    '0_9_1637223437910.526782c41fe12c3249046fedcc45563ef3662250'
    >>> generate_chunk_filename(pd.DataFrame({'A': range(10), 'B': range(10)}, index=range(10,20)))
    '10_19_1637223490719.526782c41fe12c3249046fedcc45563ef3662250'
    >>> generate_chunk_filename(pd.DataFrame({'A': []}, index=[]))
    IndexError: index 0 is out of bounds for axis 0 with size 0
    """
    first_idx, last_idx = dataframe.index[0], dataframe.index[-1]
    if isinstance(dataframe.index, pd.DatetimeIndex):
        first_idx, last_idx = dataframe.index[0].value, dataframe.index[-1].value

    shape_str = '_'.join(f'{cn}:{dt}' for cn, dt in dataframe.dtypes.items())
    shape = hashlib.sha1(shape_str.encode()).hexdigest()
    cur_time = round(time.time() * 1000)
    return f'{first_idx}_{last_idx}_{cur_time}.{shape}'


def build_chunk_metadata(dataframe: pd.DataFrame) -> dict:
    """Returns dataframe metadata
    Other metadata such as start_index or stop_index are saved into the chunk filename

    >>> build_chunk_metadata(pd.DataFrame({'A': [1,2,3], 'B': [4,5,6]}, index=[0,1,2]))
    {'columns': ['A', 'B'], 'dtypes': ['int64', 'int64'], 'nb_rows': 3, 'index_hash': 'ab2fa50ae23ce035bad2e77ec5e0be05c2f4b816'}
    """
    return {
        "columns": list(dataframe.columns),
        "dtypes": [str(dt) for dt in dataframe.dtypes],
        "nb_rows": len(dataframe.index), # TODO remove ?
        "index_hash": hashlib.sha1(dataframe.index.values).hexdigest()
    }
