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
from dataclasses import dataclass, field
from collections import namedtuple
from typing import Dict, Iterable, List, Optional
from app.bulk_persistence.dask.errors import BulkNotProcessable

from app.utils import capture_timings

from . import storage_path_builder as pathBuilder


@dataclass
class BulkCatalog:
    """Represent a bulk catalog
    Exemple:
        {
            'columns' : {
                'A' : {
                    'paths' : ['folder/file1.parquet', 'folder/file2.parquet']
                    'dtype: 'Float32'
                }
                'B' : { ... }
            },
            nb_rows: 1000,
            index_path: 'folder/wdms_index/index.parquet
        }
    """

    @dataclass
    class ColumnInfo:
        """Stores chunk files where the column is present and the dtype"""
        paths: List[str]
        dtype: str

    columns: Dict[str, ColumnInfo] = field(default_factory=dict)
    nb_rows: int = 0
    index_path: Optional[str] = None

    def add_column_info(self, col_name: str, column_info: ColumnInfo, check_dtype: bool = False):
        """Add column information to the catalog.
        If the column already exist in the catalog, merge information.
        Args:
            col_name (str): column name
            column_info (ColumnInfo): column information to add in the catalog
            check_dtype (bool, optional): check if dtype are equal before merging column info. Defaults to False.
        Raises:
            BulkNotProcessable: If check_type True and column type is different from existing one
        Exemples:
        >>> cat.add_column_info('A', BulkCatalog.ColumnInfo(['file1'], 'int32'))
        >>> cat.columns
        {'A': BulkCatalog.ColumnInfo(paths=['file1'], dtype='int32')}
        >>> cat.add_column_info('A', BulkCatalog.ColumnInfo(['file2', 'file3'], 'int32'))
        >>> cat.columns
        {'A': BulkCatalog.ColumnInfo(paths=['file1', 'file2', 'file3'], dtype='int32')}
        >>> cat.add_column_info('A', BulkCatalog.ColumnInfo(['file4'], 'int64'), True)
        BulkNotProcessable: bulk not processable: column A has different dtypes, int32 vs int64
        """
        if col_name in self.columns:
            if check_dtype and self.columns[col_name].dtype != column_info.dtype:
                raise BulkNotProcessable(message=f"column {col_name} has different dtypes,"
                                         f" {self.columns[col_name].dtype} vs {column_info.dtype}")
            self.columns[col_name].paths.extend(column_info.paths)  # TODO check if file already exists ?
        else:
            self.columns[col_name] = column_info

    ColumnsPaths = namedtuple('ColumnsPaths', ['columns', 'paths'])

    def get_paths_for_columns(self, columns: Iterable[str], root_path: str = '') -> List[ColumnsPaths]:
        """Returns the paths to load data of the requested columns grouped by paths
        Warning: it implies that paths are identicaly formated (a/b vs a\\b)
        """
        groupped_files = {}
        for col_name in columns:
            files_list = self.columns[col_name].paths
            paths = [pathBuilder.join(root_path, f) for f in files_list]
            default = self.ColumnsPaths(columns=[], paths=paths)
            groupped_files.setdefault(tuple(files_list), default).columns.append(col_name)
        return groupped_files.values()

    @capture_timings('as_dict')
    def as_dict(self) -> dict:
        """return the dict representation of the catalog"""
        return {
            "columns": {c: {
                "paths": v.paths,
                "dtype": v.dtype
            } for c, v in self.columns.items()},
            "nb_rows": self.nb_rows,
            "index_path": self.index_path
        }

    @staticmethod
    def from_dict(catalog_as_dict: dict) -> "BulkCatalog":
        """construct a Catalog from a dict"""
        catalog_as_dict['columns'] = {
            c: BulkCatalog.ColumnInfo(**v) for c, v in catalog_as_dict['columns'].items()
        }
        return BulkCatalog(**catalog_as_dict)


CATALOG_FILE_NAME = 'bulk_catalog.json'

@capture_timings('save_bulk_catalog')
def save_bulk_catalog(filesystem, folder_path: str, catalog: BulkCatalog) -> str:
    """save a bulk catalog to a json file in the given folder path"""
    folder_path, _ = pathBuilder.remove_protocol(folder_path)
    meta_path = pathBuilder.join(folder_path, CATALOG_FILE_NAME)
    with filesystem.open(meta_path, 'w') as outfile:
        data = json.dumps(catalog.as_dict())
        outfile.write(data)
        #json.dump(catalog.as_dict(), outfile) # writting with dump is slow ?


@capture_timings('load_bulk_catalog')
def load_bulk_catalog(filesystem, folder_path: str) -> BulkCatalog:
    """load a bulk catalog from a json file in the given folder path"""
    folder_path, _ = pathBuilder.remove_protocol(folder_path)
    meta_path = pathBuilder.join(folder_path, CATALOG_FILE_NAME)
    if filesystem.exists(meta_path):  # TODO may be faster with EAFP !
        with filesystem.open(meta_path) as json_file:
            data = json.load(json_file)
            return BulkCatalog.from_dict(data)
    return None
