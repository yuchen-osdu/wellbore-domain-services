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
from os.path import join, relpath
from typing import Optional, Tuple
from uuid import UUID


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
    If no protocol in path then protocol=''
    >>> remove_protocol('s3://path/to/my/file')
    ('path/to/my/file', 's3')
    >>> remove_protocol('path/to/my/file')
    ('path/to/my/file', '')
    """
    if '://' not in path:
        return path, ''
    sep_idx = path.index('://')
    return path[sep_idx + 3:], path[:sep_idx]


def record_path(
    base_directory: str, record_id, protocol: Optional[str] = None
) -> str:
    """Return the entity path.
    (path where all data relateed to an entity are saved"""
    encoded_id = hash_record_id(record_id)
    base_path = build_base_path(base_directory, protocol)
    return join(base_path, encoded_id) if base_path else encoded_id


def record_bulk_path(
    base_directory: str, record_id: str, bulk_id: str, protocol: Optional[str] = None
) -> str:
    """Return the path corresponding to the specified bulk."""
    entity_path = record_path(base_directory, record_id, protocol)
    return join(entity_path, 'bulk', bulk_id, 'data')


def record_statistics_base_path(
    base_directory: str, record_id: str, bulk_id: str, statistics_suffix: str, protocol: Optional[str] = None
) -> str:
    """Return the path corresponding to the statistics of specified bulk."""
    entity_path = record_path(base_directory, record_id, protocol)
    return join(entity_path, 'bulk', bulk_id, statistics_suffix)


def record_session_path(
    base_directory: str, session_id: UUID, record_id: str, protocol: Optional[str] = None
) -> str:
    """Return the path corresponding to the specified session."""
    entity_path = record_path(base_directory, record_id, protocol)
    return join(entity_path, 'session', str(session_id), 'data')


def record_relative_path(base_directory: str, record_id: str, path: str) -> str:
    """Returns the path relative to the specified record."""
    base_path = record_path(base_directory, record_id)
    path, _proto = remove_protocol(path)
    return relpath(path, base_path)


def full_path(
    base_directory: str, record_id: str, rel_path: str, protocol: Optional[str] = None
) -> str:
    """Returns the full path of a record from a relative path"""
    return join(record_path(base_directory, record_id, protocol), rel_path)
