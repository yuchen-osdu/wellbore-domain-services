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

from app.bulk_persistence.dask.bulk_catalog import BulkCatalog, ChunkGroup


def test_empty_catalog():
    catalog = BulkCatalog("id")
    assert len(catalog.all_columns_dtypes) == 0
    d = catalog.as_dict()
    assert d["recordId"] == "id"
    assert d["nbRows"] == 0
    assert d["indexPath"] == None


def test_add_multiple_chunk_group_same_schemas():
    catalog = BulkCatalog("id")
    all_paths = [ ['path1'],
                  ['path2'],
                  ['path3', 'path4']]
    for paths in all_paths:
        chunk_group = ChunkGroup(set(['A', 'B']), paths, ["Int32", "Int64"])
        catalog.add_chunk(chunk_group)

    catalog.all_columns_dtypes['A'] = 'Int32'
    catalog.all_columns_dtypes['B'] = 'Int64'

    column_path = catalog.get_paths_for_columns(['A', 'B'], 'test/')
    assert len(column_path) == 1
    assert column_path[0].labels == set(['A', 'B'])
    assert set(column_path[0].paths) == set([f'test/{p}' for paths in all_paths for p in paths])


def test_change_chukn_info():
    catalog = BulkCatalog("id")
    chunk_group = ChunkGroup(set(['A', 'B']), ['path1', 'paths2'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group)
    chunk_group = ChunkGroup(set(['A']), ['path3'], ["Float32"])
    catalog.change_columns_info(chunk_group)

    column_path = catalog.get_paths_for_columns(['A', 'B'], '')
    assert len(column_path) == 2
    assert column_path[0].labels == set('B')
    assert column_path[1].labels == set('A')
    assert column_path[1].paths == ['path3']

    catalog.all_columns_dtypes['A'] = 'Float32'

    