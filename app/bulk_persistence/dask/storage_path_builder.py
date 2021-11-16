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

"""
Utility functions that gathers method to build path for bulk storage
"""

import hashlib
from os.path import join
from time import time
from typing import Optional, Tuple

import pandas as pd


def hash_record_id(record_id: str) -> str:
    """encode the record_id to be a valid path name"""
    return hashlib.sha1(record_id.encode()).hexdigest()


def build_base_path(base_directory: str, protocol: Optional[str] = None) -> str:
    """return the base directory, add the protocol if requested"""
    return f'{protocol}://{base_directory}' if protocol else base_directory


def add_protocol(path: str, protocol: str) -> str:
    """add protocole to the path"""
    prefix = protocol + '://'
    if not path.startswith(prefix):
        return prefix + path
    return path


def remove_protocol(path: str) -> Tuple[str, str]:
    """remove protocol for path if any, return tuple[path, protocol].
    If no protocol in path then protocol='' """
    if '://' not in path:
        return path, ''
    sep_idx = path.index('://')
    return path[sep_idx + 3:], path[:sep_idx]


def record_path(base_directory: str, record_id, protocol: Optional[str] = None) -> str:
    """Return the entity path.
    (path where all data relateed to an entity are saved"""
    encoded_id = hash_record_id(record_id)
    base_path = build_base_path(base_directory, protocol)
    return join(base_path, encoded_id)


def record_bulks_root_path(
    base_directory: str, record_id, protocol: Optional[str] = None
) -> str:
    """return the path where blob are stored for the specified entity"""
    entity_path = record_path(base_directory, record_id, protocol)
    return join(entity_path, 'bulk')


def record_sessions_root_path(
    base_directory: str, record_id, protocol: Optional[str] = None
) -> str:
    """return the path where sessions are stored for the specified entity"""
    entity_path = record_path(base_directory, record_id, protocol)
    return join(entity_path, 'session')


def record_bulk_path(
    base_directory: str, record_id: str, bulk_id: str, protocol: Optional[str] = None
) -> str:
    """Return the path corresponding to the specified bulk."""
    entity_blob_path = record_bulks_root_path(base_directory, record_id, protocol)
    return join(entity_blob_path, bulk_id, 'data')


def record_session_path(
    base_directory: str, session_id: str, record_id: str, protocol: Optional[str] = None
) -> str:
    """Return the path corresponding to the specified session."""
    entity_session_path = record_sessions_root_path(base_directory, record_id, protocol)
    return join(entity_session_path, session_id, 'data')


def build_chunk_filename(dataframe: pd.DataFrame) -> str:
    """Return chunk file name sorted by starting index
    Note 1: do not change the name without updating SessionFileMeta
    Note 2: dask reads and sort files by 'natural_key' so the filenames impacts the final result
    """
    first_idx, last_idx = dataframe.index[0], dataframe.index[-1]
    if isinstance(dataframe.index, pd.DatetimeIndex):
        first_idx, last_idx = dataframe.index[0].value, dataframe.index[-1].value

    #shape_str = '_'.join(f'{cn}:{dt}' for cn, dt in dataframe.dtypes.items())
    shape_str = '_'.join(f'{cn}' for cn, dt in dataframe.dtypes.items())
    shape = hashlib.sha1(shape_str.encode()).hexdigest()
    cur_time = round(time() * 1000)
    return f'{first_idx}_{last_idx}_{cur_time}.{shape}'
