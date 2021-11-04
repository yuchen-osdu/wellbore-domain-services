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
    def columns(self):
        return self._read_meta()['columns']
    
    @property
    def dtypes(self):
        return self._read_meta()['dtypes']
    
    @property
    def nb_rows(self):
        return self._read_meta()['nb_rows']

    @property
    def index_hash(self):
        return self._read_meta()['index_hash']
        

    def overlap(self, other: 'SessionFileMeta'):
        """Returns True if indexes overlap."""
        return self.end >= other.start and other.end >= self.start

    def has_common_columns(self, other: 'SessionFileMeta'):
        """Returns True if contains common columns with others."""
        return share_items(self.columns, other.columns)


def get_output_file_name(pdf: pd.DataFrame) -> str:
    '''Return chunk file name sorted by starting index
    Note 1: do not change the name without updating SessionFileMeta
    Note 2: dask reads and sort files by 'natural_key' So the file name impact the final result
    '''
    first_idx, last_idx = pdf.index[0], pdf.index[-1]
    if isinstance(pdf.index, pd.DatetimeIndex):
        first_idx, last_idx = pdf.index[0].value, pdf.index[-1].value

    shape_str = '_'.join(f'{cn}:{dt}' for cn, dt in pdf.dtypes.items())
    shape = hashlib.sha1(shape_str.encode()).hexdigest()
    cur_time = round(time.time() * 1000)
    return f'{first_idx}_{last_idx}_{cur_time}.{shape}'
