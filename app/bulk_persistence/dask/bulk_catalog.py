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

import os
from dataclasses import dataclass, field
from typing import Dict, List

from app.utils import capture_timings


@dataclass
class BulkCatalog:
    "represent the bulk catalog"
    @dataclass
    class ColumnInfo:
        """store files where the column is present and the dtype"""
        paths: List[str]
        dtype: str

    columns: Dict[str, ColumnInfo] = field(default_factory=dict)

    def get_columns_files_groupped_by_files(self, columns, root_path='') -> List[Dict]:
        """return the paths to load the data of the requested columns"""
        groupped_files = {}
        for col_name in columns:
            files_list = self.columns[col_name].paths
            group_by = hash("".join(files_list))
            if group_by in groupped_files:
                groupped_files[group_by]["columns"].append(col_name)
            else:
                groupped_files[group_by] = {
                    "paths": [os.path.join(root_path, f) for f in files_list],
                    "columns": [col_name]
                }
        return list(groupped_files.values())

    @capture_timings('as_dict')
    def as_dict(self) -> dict:
        """return the dict representation of the catalog"""
        return {"columns": {
            c : {
                "paths": v.paths,
                "dtype": v.dtype
            } for c,v in self.columns.items()
        }}
        #return dataclasses.asdict(self)

    @staticmethod
    def from_dict(catalog_as_dict: dict) -> "BulkCatalog":
        """construct a Catalog from a dict"""
        return BulkCatalog(columns={
            c: BulkCatalog.ColumnInfo(**v) for c, v in catalog_as_dict['columns'].items()
        })
