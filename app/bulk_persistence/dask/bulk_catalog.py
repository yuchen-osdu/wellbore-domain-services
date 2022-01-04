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
This module groups function related to bulk catalog.
A catalog contains metadata of the chunks
"""
import json
from contextlib import suppress
from dataclasses import dataclass
from typing import Dict, Iterable, List, NamedTuple, Optional, Set

from dask.distributed import get_client

from app.bulk_persistence.dask.traces import submit_with_trace, add_trace_attributes
from app.helper.traces import with_trace
from app.utils import capture_timings
from .storage_path_builder import join, remove_protocol
from .utils import worker_capture_timing_handlers


@dataclass
class ChunkGroup:
    """A chunk group represent a chunk list having exactly the same schemas
    (columns labels and dtypes)"""
    labels: Set[str]
    paths: List[str]
    dtypes: List[str]


class BulkCatalog:
    """Represent a bulk catalog
    Example:
        {
            "recordId": "7507fb30-9cfa-4506-9cd8-6cbacbcda740",
            "nbRows": 1000,
            "indexPath": "folder/wdms_index/index.parquet,
            "columns" : [
                {
                    "labels": ["A", "B"],
                    "paths": ["folder/file1.parquet", "folder/file2.parquet"],
                    "dtypes": ["Int64, "Float32"]
                },
                {
                    "labels": ["C"],
                    "paths": ["folder/file3.parquet"],
                    "dtypes": ["Float32"]
                }
            ],
        }
    """

    def __init__(self, record_id: str) -> None:
        self.record_id: str = record_id  # TODO remove
        self.nb_rows: int = 0
        self.index_path: Optional[str] = None
        self.columns: List[ChunkGroup] = []

    @property
    def all_columns_count(self) -> int:
        """
        Return number of columns contained in bulk data
        """
        return len(self.all_columns_dtypes)

    @property
    def all_columns_dtypes(self) -> Dict[str, str]:
        """Returns all columns with their dtype
        Returns:
            Dict[str, str]:  a dict { column label : column dtype }
        """
        res = {}
        for col_group in self.columns:
            res.update({cn: dt for cn, dt in zip(col_group.labels, col_group.dtypes)})
        return res

    def add_chunk(self, chunk_group: ChunkGroup) -> None:
        """Add ChunkGroup to the catalog."""
        if len(chunk_group.labels) == 0:
            return
        keys = frozenset(chunk_group.labels)
        chunk_group_with_same_schema = next((x for x in self.columns if len(
            keys) == len(x.labels) and all(l in keys for l in x.labels)), None)
        if chunk_group_with_same_schema:
            chunk_group_with_same_schema.paths.extend(chunk_group.paths)
        else:
            self.columns.append(chunk_group)

    def remove_columns_info(self, labels: Iterable[str]) -> None:
        """Removes columns information
        Args:
            labels (Iterable[str]): columns labels to remove
        """
        clean_needed = False
        labels_set = frozenset(labels)

        for col_group in self.columns:
            remaining_columns = {col: dt for col, dt in zip(
                col_group.labels, col_group.dtypes) if col not in labels_set}
            if len(remaining_columns) != len(col_group.labels):
                col_group.labels = set(remaining_columns.keys())
                col_group.dtypes = list(remaining_columns.values())
                clean_needed = clean_needed or len(col_group.labels) == 0
        if clean_needed:
            self.columns = [c for c in self.columns if c.labels]

    def change_columns_info(self, chunk_group: ChunkGroup) -> None:
        """Replace column information with the given one
        Args:
            chunk_group (ChunkGroup): new column information
        """
        self.remove_columns_info(chunk_group.labels)
        self.add_chunk(chunk_group)

    class ColumnsPaths(NamedTuple):
        labels: Set[str]
        paths: List[str]

    def get_paths_for_columns(self, labels: Iterable[str], base_path: str) -> List[ColumnsPaths]:
        """Returns the paths to load data of the requested columns grouped by paths"""
        grouped_files = []

        for col_group in self.columns:
            matching_columns = col_group.labels.intersection(labels)
            if matching_columns:
                grouped_files.append(self.ColumnsPaths(
                    labels=matching_columns,
                    paths=[join(base_path, f) for f in col_group.paths])
                )
        return grouped_files

    def as_dict(self) -> dict:
        """Returns the dict representation of the catalog"""
        return {
            "recordId": self.record_id,
            "nbRows": self.nb_rows,
            "indexPath": self.index_path,
            'columns': [{
                'labels': list(c.labels),
                'paths': c.paths,
                'dtypes': c.dtypes
            } for c in self.columns],
        }

    @classmethod
    def from_dict(cls, catalog_as_dict: dict) -> "BulkCatalog":
        """construct a Catalog from a dict"""
        catalog = cls(record_id=catalog_as_dict["recordId"])
        catalog.nb_rows = catalog_as_dict["nbRows"]
        catalog.index_path = catalog_as_dict["indexPath"]
        catalog.columns = [
            ChunkGroup(set(c["labels"]), c["paths"], c["dtypes"])
            for c in catalog_as_dict["columns"]
        ]
        return catalog


CATALOG_FILE_NAME = 'bulk_catalog.json'


@capture_timings('save_bulk_catalog', handlers=worker_capture_timing_handlers)
@with_trace('save_bulk_catalog')
def save_bulk_catalog(filesystem, folder_path: str, catalog: BulkCatalog) -> None:
    """save a bulk catalog to a json file in the given folder path"""
    folder_path, _ = remove_protocol(folder_path)
    meta_path = join(folder_path, CATALOG_FILE_NAME)
    with filesystem.open(meta_path, 'w') as outfile:
        data = json.dumps(catalog.as_dict(), indent=0)
        outfile.write(data)
        # json.dump(catalog.as_dict(), outfile) # don't know why json.dump is slower (local windows)

    add_trace_attributes({
        'catalog-row-count': catalog.nb_rows,
        'catalog-col-count': catalog.all_columns_count
    })


@capture_timings('load_bulk_catalog', handlers=worker_capture_timing_handlers)
@with_trace('load_bulk_catalog')
def load_bulk_catalog(filesystem, folder_path: str) -> Optional[BulkCatalog]:
    """load a bulk catalog from a json file in the given folder path"""
    folder_path, _ = remove_protocol(folder_path)
    meta_path = join(folder_path, CATALOG_FILE_NAME)
    with suppress(FileNotFoundError):
        with filesystem.open(meta_path) as json_file:
            data = json.load(json_file)
            return BulkCatalog.from_dict(data)
    return None


async def async_load_bulk_catalog(filesystem, folder_path: str) -> BulkCatalog:
    return await submit_with_trace(get_client(), load_bulk_catalog, filesystem, folder_path)


async def async_save_bulk_catalog(filesystem, folder_path: str, catalog: BulkCatalog) -> None:
    return await submit_with_trace(get_client(), save_bulk_catalog, filesystem, folder_path, catalog)
