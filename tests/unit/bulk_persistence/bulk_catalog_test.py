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

import pytest
from app.bulk_persistence.dask.bulk_catalog import BulkCatalog, ChunkGroup


def test_empty_catalog():
    catalog = BulkCatalog("id")
    assert len(catalog.all_columns_dtypes) == 0
    d = catalog.as_dict()
    assert d["recordId"] == "id"
    assert d["nbRows"] == 0
    assert d["indexPath"] is None


def test_add_multiple_chunk_group_same_schemas():
    catalog = BulkCatalog("id")
    all_paths = [ ['path1'],
                  ['path2'],
                  ['path3', 'path4']]
    for paths in all_paths:
        chunk_group = ChunkGroup({'A', 'B'}, paths, ["Int32", "Int64"])
        catalog.add_chunk(chunk_group)

    catalog.all_columns_dtypes['A'] = 'Int32'
    catalog.all_columns_dtypes['B'] = 'Int64'

    column_path = catalog.get_paths_for_columns(['A', 'B'], 'test/')
    assert len(column_path) == 1
    assert column_path[0].labels == {'A', 'B'}
    assert set(column_path[0].paths) == set([f'test/{p}' for paths in all_paths for p in paths])


def test_change_chunk_info():
    catalog = BulkCatalog("id")
    chunk_group = ChunkGroup({'A', 'B'}, ['path1', 'paths2'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group)
    chunk_group = ChunkGroup({'A'}, ['path3'], ["Float32"])
    catalog.change_columns_info(chunk_group)

    column_path = catalog.get_paths_for_columns(['A', 'B'], '')
    assert len(column_path) == 2
    assert column_path[0].labels == set('B')
    assert column_path[1].labels == set('A')
    assert column_path[1].paths == ['path3']

    assert catalog.all_columns_dtypes['A'] == 'Float32'
    assert catalog.all_columns == {'A', 'B'}


def test_get_paths_for_columns_all_columns():
    catalog = BulkCatalog("id")
    chunk_group = ChunkGroup({'A', 'B'}, ['path1', 'paths2'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group)
    chunk_group = ChunkGroup({'C', 'D'}, ['path3', 'paths4'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group)

    column_path = catalog.get_paths_for_columns(None, '')
    all_columns = {col for col_paths in column_path for col in col_paths.labels }
    excepted_columns = {'A', 'B', 'C', 'D'}
    assert all_columns == excepted_columns
    assert catalog.all_columns == all_columns


def test_filter_group_for_columns():
    catalog = BulkCatalog("id")
    chunk_group1 = ChunkGroup({'A', 'B'}, ['path1', 'paths2'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group1)
    chunk_group2 = ChunkGroup({'C', 'D'}, ['path3'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group2)

    assert catalog.filter_group_for_columns({'A'}) == [chunk_group1]
    assert catalog.filter_group_for_columns({'A', 'B'}) == [chunk_group1]
    assert catalog.filter_group_for_columns({'C', 'B'}) == [chunk_group1, chunk_group2]
    assert catalog.filter_group_for_columns({'D'}) == [chunk_group2]
    assert catalog.filter_group_for_columns({'Z'}) == []


def test_is_columns_slide_only():
    catalog = BulkCatalog("id")
    chunk_group = ChunkGroup({'A', 'B'}, ['path1', 'paths2'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group)
    chunk_group = ChunkGroup({'C', 'D'}, ['path3'], ["Int32", "Int64"])
    catalog.add_chunk(chunk_group)

    assert not catalog.is_columns_slide_only()
    assert not catalog.is_columns_slide_only({'A'})
    assert not catalog.is_columns_slide_only({'A', 'B'})
    assert not catalog.is_columns_slide_only({'A', 'C'})
    assert catalog.is_columns_slide_only({'C'})
    assert catalog.is_columns_slide_only({'D', 'C'})

    catalog = BulkCatalog("id")
    chunk_group = ChunkGroup({'A', 'B'}, ['path2'], ["Int32", "Int64"])
    chunk_group = ChunkGroup({'C', 'D'}, ['path1'], ["Int32", "Int64"])
    assert catalog.is_columns_slide_only()
    assert catalog.is_columns_slide_only({'C', 'D', 'A', 'B'})


def test_is_columns_slide_only_handle_many_columns():
    # 400 chunks with 500 columns each
    catalog = BulkCatalog("id")
    for i in range(400):
        catalog.add_chunk(ChunkGroup({f'C{i}[{j}]' for j in range(500)}, [f'path{i}'], []))

    assert catalog.is_columns_slide_only()
    assert catalog.is_columns_slide_only({f'C{i}[{j}]' for j in range(10, 70) for i in (3, 5, 100, 244)})

    catalog.add_chunk(ChunkGroup({'C2[50]'}, [f'pathX'], []))
    assert not catalog.is_columns_slide_only()
    assert catalog.is_columns_slide_only({f'C{i}[{j}]' for j in range(10, 70) for i in (3, 5, 100, 244)})
    assert not catalog.is_columns_slide_only({'C2[50]'})


@pytest.mark.slow
def test_is_describe_handle_many_columns(nope_logger_fixture):
    # mainly to track time of the test
    # as it could be a bottleneck for big array

    catalog = BulkCatalog("id")
    # generate 200 000 columns
    for i in range(25):
        catalog.add_chunk(ChunkGroup({f'C{i}[{j}]' for j in range(8000)}, [f'path{i}'], []))

    r = catalog.describe()
    assert len(r.columns) == 200_000
