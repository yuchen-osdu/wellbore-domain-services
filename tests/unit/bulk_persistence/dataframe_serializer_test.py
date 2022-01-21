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
import pandas as pd
import json
import pytest
from io import StringIO, BytesIO
from unittest.mock import patch

from tempfile import SpooledTemporaryFile

Reference_df = pd.DataFrame([[1., 10, 11], [2., 20, 21], [3., 30, 31]], columns=['ref', 'a', 'b'])


@pytest.fixture()
def data_path(tmp_path):
    yield tmp_path / 'data.json'


# we're building it manually as we want to spot any change from anywhere that could occur (in pandas for instance)
# we want format to be stable
dataframe_dict = {
    'split': {'index': Reference_df.index.tolist(),
              'columns': Reference_df.columns.tolist(),
              'data': Reference_df.values.tolist()},
    'columns': {
        str(col_val): {
            str(row_val): Reference_df[col_val].tolist()[count] for count, row_val in enumerate(Reference_df.index.tolist())
        } for col_val in Reference_df.columns.tolist()
    }
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


def test_load_from_path(data_path):
    orient = 'split'
    data_dict = dataframe_dict[orient]

    with open(data_path, 'w') as file:
        json.dump(data_dict, file)

    df = DataframeSerializerSync.read_json(data_path, orient=orient)
    check_dataframe(df)


def test_load_from_file_like(data_path):
    orient = 'split'
    data_dict = dataframe_dict[orient]

    with open(data_path, 'w') as file:
        json.dump(data_dict, file)

    with open(data_path, 'r') as file:
        df = DataframeSerializerSync.read_json(file, orient=orient)
        check_dataframe(df)


def test_load_parquet_from_file_like(tmp_path):
    path = tmp_path / 'data.parquet'
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


def test_to_json_to_path(data_path):
    orient = 'split'
    data_dict = dataframe_dict[orient]


    result = DataframeSerializerSync.to_json(Reference_df, path_or_buf=data_path, orient=orient)
    assert result is None

    with open(data_path, 'r') as file:
        actual_dict = json.load(file)
        assert actual_dict == data_dict


def test_to_json_to_file(data_path):
    orient = 'split'
    data_dict = dataframe_dict[orient]


    with open(data_path, 'w') as file:
        result = DataframeSerializerSync.to_json(Reference_df, path_or_buf=file, orient=orient)
    assert result is None

    with open(data_path, 'r') as file:
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


def test_to_parquet_to_buffer():
    result = DataframeSerializerSync.to_parquet(Reference_df)

    actual_df = pd.read_parquet(BytesIO(result))
    assert_dataframe_equals(Reference_df, actual_df)


def test_to_parquet_to_file_like():
    str_buf = BytesIO()

    result = DataframeSerializerSync.to_parquet(Reference_df, path_or_buf=str_buf)
    assert result is None

    str_buf.seek(0)
    actual_df = pd.read_parquet(str_buf)
    assert_dataframe_equals(Reference_df, actual_df)


def test_to_parquet_forward_storage_options():
    with patch.object(pd.DataFrame, 'to_parquet') as mock_to_parquet:
        DataframeSerializerSync.to_parquet(Reference_df, storage_options={"custom_opt": "custom_value"})
        mock_to_parquet.assert_called_once()
        _, kwargs = mock_to_parquet.call_args_list[0]
        assert kwargs['storage_options'] == {"custom_opt": "custom_value"}


@pytest.mark.parametrize("indexes", [['a', 'b', 'c'], [1, 2, 3], [1.1, 2.2, 3.3]])
@pytest.mark.parametrize("orient", ['split', 'columns'])
def test_case_json_keeps_index_types(indexes, orient):
    origin_df = pd.DataFrame([[1., 10], [2., 20], [3., 30]], columns=['1', '2'], index=indexes)
    json_content = origin_df.to_json(orient=orient)

    # WHEN
    actual_df = DataframeSerializerSync.read_json(json_content, orient=orient)

    # THEN columns and index are still string type
    assert actual_df.columns.tolist() == ['1', '2']

    # THEN index same type
    assert actual_df.index.tolist() == indexes


@pytest.mark.parametrize("orient", ['split', 'columns'])
def test_case_json_no_datetime_convert(orient):
    origin_df = pd.DataFrame([[1., 10], [2., 20], [3., 30]],
                             columns=['3/11/2000', '3/12/2000'],
                             index=['3/11/2000', '3/12/2000', '3/13/2000'])
    json_content = origin_df.to_json(orient=orient)

    # WHEN
    actual_df = DataframeSerializerSync.read_json(json_content, orient=orient)

    # THEN index are both string no convert to date time type
    assert actual_df.index.dtype == 'object'
    assert actual_df.columns.dtype == 'object'
