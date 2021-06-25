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

from app.bulk_persistence.dataframe_serializer import (DataframeSerializerSync,
                                                       DataframeSerializerAsync,
                                                       JSONOrient)
from tests.unit.test_utils import temp_directory
import pandas as pd
import json
import pytest
from io import StringIO, BytesIO

from tempfile import SpooledTemporaryFile

Reference_df = pd.DataFrame([[1., 10, 11], [2., 20, 21], [3., 30, 31]], columns=['ref', 'a', 'b'])
CONSTANT_DATA_JSON = '/data.json'


# we're building it manually as we want to spot any change from anywhere that could occur (in pandas for instance)
# we want format to be stable
dataframe_dict = {
    'split': {'index': Reference_df.index.tolist(),
              'columns': Reference_df.columns.tolist(),
              'data': Reference_df.values.tolist()},
    'index': {
        str(row_val): {
            str(col_val): Reference_df[col_val].tolist()[count] for col_val in Reference_df.columns.tolist()
        } for count, row_val in enumerate(Reference_df.index.tolist())
    },
    'columns': {
        str(col_val): {
            str(row_val): Reference_df[col_val].tolist()[count] for count, row_val in enumerate(Reference_df.index.tolist())
        } for col_val in Reference_df.columns.tolist()
    },
    'records': [{c: v for c, v in zip(Reference_df.columns, row_values)} for row_values in Reference_df.values]
}


def assert_dataframe_equals(lhs: pd.DataFrame, rhs: pd.DataFrame):
    assert lhs.columns.tolist() == rhs.columns.tolist()
    assert lhs.index.tolist() == rhs.index.tolist()
    assert lhs.values.tolist() == rhs.values.tolist()


def check_dataframe(df: pd.DataFrame):
    """ check against ref dataframe """
    assert_dataframe_equals(df, Reference_df)


@pytest.mark.parametrize("orient", [o for o in JSONOrient])
def test_schema(orient):
    assert DataframeSerializerSync.get_schema(orient)


@pytest.mark.parametrize("data_dict,orient", [(d, o) for o, d in dataframe_dict.items()])
def test_load_from_str_various_orient(data_dict, orient):
    print(orient)
    dataframe_json = json.dumps(data_dict)
    print(dataframe_json)
    df = DataframeSerializerSync.read_json(dataframe_json, orient=orient)
    check_dataframe(df)


def test_load_from_path(temp_directory):
    orient = 'split'
    data_dict = dataframe_dict[orient]
    path = temp_directory + CONSTANT_DATA_JSON
    with open(path, 'w') as file:
        json.dump(data_dict, file)

    df = DataframeSerializerSync.read_json(path, orient=orient)
    check_dataframe(df)


def test_load_from_file_like(temp_directory):
    orient = 'split'
    data_dict = dataframe_dict[orient]
    path = temp_directory + CONSTANT_DATA_JSON
    with open(path, 'w') as file:
        json.dump(data_dict, file)

    with open(path, 'r') as file:
        df = DataframeSerializerSync.read_json(file, orient=orient)
        check_dataframe(df)


def test_load_parquet_from_file_like(temp_directory):
    path = temp_directory + '/data.parquet'
    Reference_df.to_parquet(path)

    with open(path, 'rb') as file:
        df = DataframeSerializerSync.read_parquet(file)
        check_dataframe(df)

    buffer = BytesIO()
    Reference_df.to_parquet(buffer)
    df = DataframeSerializerSync.read_parquet(buffer)
    check_dataframe(df)


def test_load_parquet_from_spooled_file():
    max_size = 2000

    # small one
    spooled_file = SpooledTemporaryFile(max_size=max_size)
    frame = pd.DataFrame([1], columns=['r'])
    frame.to_parquet(spooled_file)
    assert not spooled_file._rolled  # ensure on buffer mode
    df = DataframeSerializerSync.read_parquet(spooled_file)
    assert df.equals(frame)

    # bigger one
    spooled_file = SpooledTemporaryFile(max_size=max_size)
    frame = pd.DataFrame(list(range(max_size)), columns=['r'])
    frame.to_parquet(spooled_file)
    assert spooled_file._rolled  # ensure on file mode
    df = DataframeSerializerSync.read_parquet(spooled_file)
    assert df.equals(frame)


@pytest.mark.parametrize("data_dict,orient", [(d, o) for o, d in dataframe_dict.items()])
def test_to_json_str_various_orient(data_dict, orient):
    result = DataframeSerializerSync.to_json(Reference_df, orient=orient)
    actual_dict = json.loads(result)
    assert actual_dict == data_dict


@pytest.mark.asyncio
async def test_back_forth_async_serializer():
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(1)
    serializer = DataframeSerializerAsync(executor)

    as_json = await serializer.to_json(Reference_df, orient='split')
    df = DataframeSerializerSync.read_json(as_json, orient='split')
    check_dataframe(df)

    df = await serializer.read_json(as_json, orient='split')
    check_dataframe(df)


def test_to_json_to_path(temp_directory):
    orient = 'split'
    data_dict = dataframe_dict[orient]
    path = temp_directory + CONSTANT_DATA_JSON

    result = DataframeSerializerSync.to_json(Reference_df, path_or_buf=path, orient=orient)
    assert result is None

    with open(path, 'r') as file:
        actual_dict = json.load(file)
        assert actual_dict == data_dict


def test_to_json_to_file(temp_directory):
    orient = 'split'
    data_dict = dataframe_dict[orient]
    path = temp_directory + CONSTANT_DATA_JSON

    with open(path, 'w') as file:
        result = DataframeSerializerSync.to_json(Reference_df, path_or_buf=file, orient=orient)
    assert result is None

    with open(path, 'r') as file:
        actual_dict = json.load(file)
        assert actual_dict == data_dict


def test_to_json_to_file_like():
    orient = 'split'
    data_dict = dataframe_dict[orient]
    str_buf = StringIO()
    result = DataframeSerializerSync.to_json(Reference_df, path_or_buf=str_buf, orient=orient)
    assert result is None

    str_buf.seek(0)
    actual_dict = json.loads(str_buf.read())
    assert actual_dict == data_dict
