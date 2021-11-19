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
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from app.utils import capture_timings

from . import storage_path_builder as pathBuilder


# TODO
# is Catalog a good naming ?
# choose a proper name for the catalog now it is "_meta.json"
@dataclass
class BulkCatalog:
    "represent the bulk catalog"
    @dataclass
    class ColumnInfo:
        """store files where the column is present and the dtype"""
        paths: List[str]
        dtype: str

    columns: Dict[str, ColumnInfo] = field(default_factory=dict)
    nb_rows: int = 0
    index_path: Optional[str] = None

    def get_paths_for_columns(self, columns: Iterable[str], root_path: str = '') -> List[Dict]:
        """Returns the paths to load data of the requested columns grouped by paths"""
        groupped_files = {}
        for col_name in columns:
            files_list = self.columns[col_name].paths
            groupped_files.setdefault(hash(tuple(files_list)), {
                "paths": [os.path.join(root_path, f) for f in files_list],
                "columns": []
            })["columns"].append(col_name)
        return list(groupped_files.values())

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
        #return dataclasses.asdict(self)

    @staticmethod
    def from_dict(catalog_as_dict: dict) -> "BulkCatalog":
        """construct a Catalog from a dict"""
        catalog_as_dict['columns'] = {
            c: BulkCatalog.ColumnInfo(**v) for c, v in catalog_as_dict['columns'].items()
        }
        return BulkCatalog(**catalog_as_dict)


CATALOG_FILE_NAME = '_meta.json'


def save_bulk_catalog(filesystem, folder_path: str, catalog: BulkCatalog) -> str:
    """save a bulk catalog to a json file in the given folder path"""
    folder_path, _ = pathBuilder.remove_protocol(folder_path)
    meta_path = pathBuilder.join(folder_path, CATALOG_FILE_NAME)
    with filesystem.open(meta_path, 'w') as outfile:
        json.dump(catalog.as_dict(), outfile)


def load_bulk_catalog(filesystem, folder_path: str) -> BulkCatalog:
    """load a bulk catalog from a json file in the given folder path"""
    folder_path, _ = pathBuilder.remove_protocol(folder_path)
    meta_path = pathBuilder.join(folder_path, CATALOG_FILE_NAME)
    if filesystem.exists(meta_path):  # TODO may be faster with EAFP !
        with filesystem.open(meta_path) as json_file:
            data = json.load(json_file)
            return BulkCatalog.from_dict(data)
    return None
