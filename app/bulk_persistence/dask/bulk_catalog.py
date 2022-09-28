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
from typing import Dict, Iterable, Iterator, List, NamedTuple, Optional, Set
from itertools import chain
from io import BytesIO

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.exceptions import ResourceNotFoundException

from .session_file_meta import is_chunk_filename
from ..capture_timings import timeit, capture_timings
from ..model_chunking import DataframeDescribe
from ..dataframe_columns import ColumnSelection, select_columns, sort_column_labels
from .storage_path_builder import join, record_bulk_path, basename


@dataclass
class ChunkGroup:
    """A chunk group represent a chunk list having exactly the same schemas
    (columns labels and dtypes)"""
    labels: Set[str]
    paths: List[str]
    dtypes: List[str]


ColumnLabel = str
ColumnDType = str


class BulkCatalogOrigin:
    def __init__(self):
        self._origin_type = 0  # internal, 0 = unknown, 1 = generated from bulk, 2 loaded from file

    @classmethod
    def from_file(cls):
        inst = cls()
        inst._origin_type = 2
        return inst

    @classmethod
    def generated_from_bulk(cls):
        inst = cls()
        inst._origin_type = 1
        return inst

    @property
    def was_generated(self) -> bool:
        return self._origin_type == 1


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

    def __init__(self, record_id: str, origin: Optional[BulkCatalogOrigin] = None) -> None:
        self._record_id: str = record_id
        self.nb_rows: int = 0
        self.index_path: Optional[str] = None
        self._columns: List[ChunkGroup] = []
        self.origin = origin or BulkCatalogOrigin()  # not persisted

        # cached attributes, to be cleaned as soon as _columns change
        self._columns_labels: Optional[Set[str]] = None
        self._columns_dtypes = None

    @property
    def record_id(self) -> str:
        return self._record_id

    @property
    def all_columns_count(self) -> int:
        """
        Return number of columns contained in bulk data
        """
        return len(self.all_columns)

    def is_columns_slide_only(self, columns_to_check: Optional[Set[str]] = None) -> bool:
        """
        return True if the bulk is only cut by columns, i.e. there's one and only one chunk to read to get full column
        """
        column_label_set: Set[str] = set()
        previous_size = 0
        if columns_to_check is None:
            for chunk_group in self._columns:
                if len(chunk_group.paths) > 1:
                    return False
                column_label_set.update(chunk_group.labels)
                if previous_size + len(chunk_group.labels) > len(column_label_set):
                    return False
                previous_size = len(column_label_set)
            return True

        # case few columns only
        for chunk_group in self._columns:
            intersect = chunk_group.labels.intersection(columns_to_check)
            if not intersect:
                continue

            if len(chunk_group.paths) > 1:
                return False

            if not column_label_set.isdisjoint(intersect):
                # it's mean there's already on chunk for one element in intersect
                return False
            column_label_set.update(intersect)

        return True

    @property
    def all_columns_dtypes(self) -> Dict[ColumnLabel, ColumnDType]:
        """Returns all columns with their dtype
        Returns:
            Dict[str, str]:  a dict { column label : column dtype }
        """
        if self._columns_dtypes is not None:
            return self._columns_dtypes
        res = {}
        for col_group in self._columns:
            res.update({cn: dt for cn, dt in zip(col_group.labels, col_group.dtypes)})
        self._columns_dtypes = res
        return res

    def _clean_column_cache(self):
        self._columns_labels = None
        self._columns_dtypes = None

    @property
    def all_columns(self) -> Set[str]:
        if self._columns_labels is None:
            self._columns_labels = set(chain.from_iterable((col_group.labels for col_group in self._columns)))
        return self._columns_labels

    @property
    def chunk_count(self) -> int:
        # TODO by design, a path should not appears twice but nothing prevent to construct a catalog with the same
        #  chunk path more than once, so let's use a set container for now
        return len(set(self.get_chunk_paths()))

    def get_chunk_paths(self) -> Iterator[str]:
        """ iterator over all paths """
        return chain.from_iterable((col_group.paths for col_group in self._columns))

    @staticmethod
    def is_single_file_chunk(chunk_path) -> bool:
        """ differentiate a single chunk from a multi partition dataframe saved by Dask. returns True if chunk is a
        lonely parquet file"""
        # so far the simplest and fastest (loose) way is to check if the file_name match a chunk file name generated
        # from session_file_meta. Luckily the only way chunk is generated using Dask is when conflict resolution
        # happen and the name format is different (just a uuid)
        # Another way would be to check is the path point to a file (raw chunk) or a folder (Dask multi partition)
        return is_chunk_filename(basename(chunk_path))

    def add_chunk(self, chunk_group: ChunkGroup) -> None:
        """Add ChunkGroup to the catalog."""
        if len(chunk_group.labels) == 0:
            return

        self._clean_column_cache()
        keys = frozenset(chunk_group.labels)
        chunk_group_with_same_schema = next((x for x in self._columns if len(
            keys) == len(x.labels) and all(l in keys for l in x.labels)), None)
        if chunk_group_with_same_schema:
            chunk_group_with_same_schema.paths.extend(chunk_group.paths)
        else:
            self._columns.append(chunk_group)

    def remove_columns_info(self, labels: Iterable[str]) -> None:
        """Removes columns information
        Args:
            labels (Iterable[str]): columns labels to remove
        """

        self._clean_column_cache()
        clean_needed = False
        labels_set = frozenset(labels)

        for col_group in self._columns:
            remaining_columns = {col: dt for col, dt in zip(
                col_group.labels, col_group.dtypes) if col not in labels_set}
            if len(remaining_columns) != len(col_group.labels):
                col_group.labels = set(remaining_columns.keys())
                col_group.dtypes = list(remaining_columns.values())
                clean_needed = clean_needed or len(col_group.labels) == 0
        if clean_needed:
            self._columns = [c for c in self._columns if c.labels]

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
        """Returns the paths to load data of the requested columns grouped by paths
        Args:
            labels (Iterable[str]): List of desired columns. If None or empty select all columns.
            base_path (str): Base path as prefix to chunks path
        Returns:
            List[ColumnsPaths]: The requested columns grouped by paths
        """
        grouped_files = []

        for col_group in self._columns:
            matching_columns = col_group.labels.intersection(labels) if labels else col_group.labels
            if matching_columns:
                grouped_files.append(self.ColumnsPaths(
                    labels=matching_columns,
                    paths=[join(base_path, f) for f in col_group.paths])
                )
        return grouped_files

    def filter_group_for_columns(self, labels: Set[str]) -> List[ChunkGroup]:
        return [col_group for col_group in self._columns if not col_group.labels.isdisjoint(labels)]

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
            } for c in self._columns],
        }

    def describe(self, *,
                 offset: Optional[int] = None,
                 limit: Optional[int] = None,
                 column_selection: Optional[ColumnSelection] = None) -> DataframeDescribe:
        nb_rows = self.nb_rows
        if offset:
            nb_rows = max(0, nb_rows - offset)
        if limit:
            nb_rows = min(nb_rows, limit)

        all_columns = self.all_columns
        if column_selection:
            columns, _ = select_columns(column_selection, all_columns)
        else:
            with timeit(f"sort {len(self.all_columns)} columns using natsorted"):
                columns = sort_column_labels(self.all_columns)

        # use construct to prevent validation of pydantic
        return DataframeDescribe.construct(
            numberOfRows=nb_rows,
            columns=columns
        )

    @classmethod
    def from_dict(cls, catalog_as_dict: dict) -> "BulkCatalog":
        """construct a Catalog from a dict"""
        catalog = cls(record_id=catalog_as_dict["recordId"])
        catalog.nb_rows = catalog_as_dict["nbRows"]
        catalog.index_path = catalog_as_dict["indexPath"]
        catalog._columns = [
            ChunkGroup(set(c["labels"]), c["paths"], c["dtypes"])
            for c in catalog_as_dict["columns"]
        ]
        return catalog


CATALOG_FILE_NAME = 'bulk_catalog.json'


def _get_persistence_path(record_id: str, bulk_id: str) -> str:
    folder_path = record_bulk_path('', record_id, bulk_id)  # because base_directory already inside tenant
    return join(folder_path, CATALOG_FILE_NAME)


@capture_timings("async_load_bulk_catalog_with_blob_storage")
async def async_load_bulk_catalog_with_blob_storage(record_id: str,
                                                    bulk_id: str,
                                                    tenant=None,
                                                    storage: Optional[BlobStorageBase] = None
                                                    ) -> Optional[BulkCatalog]:
    # TODO it would be better to not get the tenant and BlobStorage from context at all,
    #  currently done this way at first to ease migrating
    from app.context import get_ctx
    ctx = get_ctx()
    tenant = tenant or ctx.tenant
    storage = storage or await ctx.app_injector.get(BlobStorageBase)

    storage_full_name = _get_persistence_path(record_id, bulk_id)
    with suppress(ResourceNotFoundException):
        with timeit("async download bulk_catalog"):
            content = await storage.download(tenant, storage_full_name)

        with timeit(f"parse download bulk_catalog of size {len(content)}"):
            data = json.load(BytesIO(content))
            return BulkCatalog.from_dict(data)
    return None


@capture_timings("async_save_bulk_catalog_with_blob_storage")
async def async_save_bulk_catalog_with_blob_storage(record_id: str,
                                                    bulk_id: str,
                                                    catalog: BulkCatalog,
                                                    tenant=None,
                                                    storage: Optional[BlobStorageBase] = None
                                                    ) -> None:
    # TODO it would be better to not get the tenant and BlobStorage from context at all,
    #  currently done this way at first to ease migrating
    from app.context import get_ctx
    ctx = get_ctx()
    tenant = tenant or ctx.tenant
    storage = storage or await ctx.app_injector.get(BlobStorageBase)

    storage_full_name = _get_persistence_path(record_id, bulk_id)

    # TODO it might be possible to directly dump as bytes by passing the encoding
    with timeit("json dumps bulk_catalog"):
        json_bytes = json.dumps(catalog.as_dict(), indent=0).encode()

    with timeit(f"upload bulk_catalog of size {len(json_bytes)}"):
        await storage.upload(tenant, storage_full_name, BytesIO(json_bytes))
