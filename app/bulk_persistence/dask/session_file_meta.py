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
from typing import List

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

    def overlap(self, other: 'SessionFileMeta') -> bool:
        """Returns True if indexes overlap."""
        return self.end >= other.start and other.end >= self.start

    def has_common_columns(self, other: 'SessionFileMeta') -> bool:
        """Returns True if contains common columns with others."""
        return share_items(self.columns, other.columns)
