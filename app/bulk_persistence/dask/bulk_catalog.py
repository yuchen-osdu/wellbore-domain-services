import dataclasses
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class BulkCatalog:
    "represent the bulk catalog"
    @dataclass
    class ColumnInfo:
        """store files where the column is present and the dtype"""
        paths: List[str]
        dtype: str

    columns: Dict[str, ColumnInfo] = field(default_factory=dict)

    def get_columns_files_groupped_by_files(self, columns) -> List[Dict]:
        """return the paths to load the data of the requested columns"""
        groupped_files = {}
        for col_name in columns:
            files_list = self.columns[col_name].paths
            group_by = hash("".join(files_list))
            if group_by in groupped_files:
                groupped_files[group_by]["columns"].append(col_name)
            else:
                groupped_files[group_by] = {"paths" : files_list, "columns": [col_name]}
        return list(groupped_files.values())

    def as_dict(self) -> dict:
        """return the dict representation of the catalog"""
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(catalog_as_dict: dict) -> "BulkCatalog":
        """construct a Catalog from a dict"""
        return BulkCatalog(columns={
            c: BulkCatalog.ColumnInfo(**v) for c, v in catalog_as_dict['columns'].items()
        })
