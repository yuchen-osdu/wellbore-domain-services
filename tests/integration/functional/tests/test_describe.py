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

from .test_chunking import ParquetSerializer, JsonSerializer, create_record, build_request_post_data, \
    build_request, build_base_url, create_session, \
    build_request_post_chunk, complete_session
from ..generate_dataframe import generate_df

from wdms_client.request_runner import RequestRunner
from .fixtures import with_wdms_env


def build_request_get_data_describe(entity_type: str, record_id: str, filters=None) -> RequestRunner:
    url = build_base_url(entity_type) + f'/{record_id}/data'
    url = url + '?' + 'describe=true'
    if filters:
        url = url + '?' + '&'.join(f'{k}={v}' for k, v in filters.items())

    return build_request(f'{entity_type} get data', 'GET', url)


def create_data_without_session(with_wdms_env, record_id, serializer, data, entity_type, headers):
    data_to_send = serializer.dump(data)
    build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()


def create_data_with_session(with_wdms_env, record_id, serializer, data, entity_type):
    data_to_send = serializer.dump(data)
    # create session
    session_id = create_session(with_wdms_env, entity_type, record_id, True)  # mode overwrite
    build_request_post_chunk(
        entity_type, record_id, session_id, data_to_send
    ).call(
        with_wdms_env, headers={'Content-Type': serializer.mime_type},
    ).assert_ok()
    # commit session
    complete_session(with_wdms_env, entity_type, record_id, session_id, True)  # commit


@pytest.mark.tag('describe', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory"])
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
def test_describe_one_chunk_without_session(with_wdms_env, entity_type, serializer):
    col_and_nb_col = {'MD': 1, 'X': 1}
    data = generate_df(col_and_nb_col.keys(), range(8))
    headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        create_data_without_session(with_wdms_env, record_id, serializer, data, entity_type, headers)

        result = build_request_get_data_describe(entity_type, record_id).call(with_wdms_env, headers=headers,
                                                                              assert_status=200)
        res_as_dict = result.response.json()
        assert res_as_dict["numberOfRows"] == 8
        assert res_as_dict["columns"] == ["MD", "X"]


@pytest.mark.tag('describe', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory"])
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
def test_describe_one_chunk_with_session_commit(with_wdms_env, entity_type, serializer):

    col_and_nb_col = {'MD': 1, 'X': 1}
    expected = generate_df(col_and_nb_col.keys(), range(8))
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        create_data_with_session(with_wdms_env, record_id, serializer, expected, entity_type)

        # then check describe
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
        result = build_request_get_data_describe(entity_type, record_id).call(with_wdms_env, headers=headers,
                                                                              assert_status=200)
        res_as_dict = result.response.json()
        assert res_as_dict["numberOfRows"] == 8
        assert res_as_dict["columns"] == ["MD", "X"]


@pytest.mark.tag('describe', 'smoke')
def test_describe_multiple_chunks_with_session_commit(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1, 'Y': 1, 'Z': 1}
    data = generate_df(col_and_nb_col.keys(), range(1000))
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        create_data_with_session(with_wdms_env, record_id, serializer, data, entity_type)
        # then check describe
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
        result = build_request_get_data_describe(entity_type, record_id).call(with_wdms_env, headers=headers,
                                                                              assert_status=200)
        res_as_dict = result.response.json()
        assert res_as_dict["numberOfRows"] == 1000
        assert res_as_dict["columns"] == ["MD", "X", "Y", "Z"]


@pytest.mark.tag('chunking', 'smoke')
def test_describe_with_offset_filter_without_session(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1}
    size = 100
    data = generate_df(col_and_nb_col.keys(), range(size))
    headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
    with create_record(with_wdms_env, entity_type,col_and_nb_col) as record_id:
        create_data_without_session(with_wdms_env, record_id, serializer, data, entity_type, headers)

        validation_list = [  # tuple (params, expected_status, expected data)
            ({"offset": 0}, 200, data),
            ({"offset": "0"}, 200, data),
            ({"offset": 1}, 200, data.tail(size - 1)),
            ({"offset": int(size / 2)}, 200, data.tail(int(size / 2))),
            ({"offset": size - 1}, 200, data.tail(1)),
            ({"offset": 1, "curves": "X"}, 200, data[['X']].tail(size - 1)),
            # if offset >= number of rows, returns an empty dataFrame with columns
            ({"offset": size}, 200, data.tail(0)),
            ({"offset": size + 50}, 200, data.tail(0)),
            # invalid offset
            ({"offset": -2}, 422, None),
            ({"offset": "false"}, 422, None)
        ]

        for (params, expected_status, expected_data) in validation_list:
            headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
            result = build_request_get_data_describe(entity_type, record_id
                                                     ).call(with_wdms_env,
                                                            params=params,
                                                            headers=headers,
                                                            assert_status=expected_status)
            if result.ok:
                res_as_dict = result.response.json()
                assert res_as_dict["numberOfRows"] == len(expected_data.index)
                assert res_as_dict["columns"] == expected_data.columns.tolist()


@pytest.mark.tag('chunking', 'smoke')
def test_describe_with_offset_filter_with_session(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1}
    size = 100
    data = generate_df(col_and_nb_col.keys(), range(size))
    with create_record(with_wdms_env, entity_type,col_and_nb_col) as record_id:
        create_data_with_session(with_wdms_env, record_id, serializer, data, entity_type)

        validation_list = [  # tuple (params, expected_status, expected data)
            ({"offset": 0}, 200, data),
            ({"offset": "0"}, 200, data),
            ({"offset": 1}, 200, data.tail(size - 1)),
            ({"offset": int(size / 2)}, 200, data.tail(int(size / 2))),
            ({"offset": size - 1}, 200, data.tail(1)),
            ({"offset": 1, "curves": "X"}, 200, data[['X']].tail(size - 1)),
            # if offset >= number of rows, returns an empty dataFrame with columns
            ({"offset": size}, 200, data.tail(0)),
            ({"offset": size + 50}, 200, data.tail(0)),
            # invalid offset
            ({"offset": -2}, 422, None),
            ({"offset": "false"}, 422, None)
        ]

        for (params, expected_status, expected_data) in validation_list:
            headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
            result = build_request_get_data_describe(entity_type, record_id
                                                     ).call(with_wdms_env,
                                                            params=params,
                                                            headers=headers,
                                                            assert_status=expected_status)
            if result.ok:
                res_as_dict = result.response.json()
                assert res_as_dict["numberOfRows"] == len(expected_data.index)
                assert res_as_dict["columns"] == expected_data.columns.tolist()


@pytest.mark.tag('describe', 'smoke')
def test_describe_with_column_filter_without_session(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1, 'Y': 1, 'Z': 1, '2D': 3}
    size = 100
    data = generate_df(['MD', 'X', 'Y', 'Z', '2D[0]', '2D[1]', '2D[2]'], range(size))
    headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        create_data_without_session(with_wdms_env, record_id, serializer, data, entity_type, headers)

        validation_list = [  # tuple (params, expected_status, expected data)
            ({"curves": "MD"}, 200, data[['MD']]),
            ({"curves": "X, Y, Z"}, 200, data[['X', 'Y', 'Z']]),
            # Behavior change compared to without worker. # But we agree this should return 404
            ({"curves": "W, X"}, 200, data[['X']]),
            ({"curves": "2D[0]"}, 200, data[['2D[0]']]),
            ({"curves": "2D[0:1]"}, 200, data[['2D[0]', '2D[1]']]),
            ({"curves": "2D"}, 200, data[['2D[0]', '2D[1]', '2D[2]']]),
            ({"curves": "Y, X"}, 200, data[['Y', 'X']]),  # filter order should be maintain
            ({"curves": "2D[1], 2D[0]"}, 200, data[['2D[1]', '2D[0]']]),  # filter order should be maintain
        ]

        for (params, expected_status, expected_data) in validation_list:
            headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
            result = build_request_get_data_describe(entity_type, record_id
                                                     ).call(with_wdms_env,
                                                            params=params,
                                                            headers=headers,
                                                            assert_status=expected_status)
            if result.ok:
                res_as_dict = result.response.json()
                assert res_as_dict["numberOfRows"] == len(expected_data.index)
                assert res_as_dict["columns"] == expected_data.columns.tolist()


@pytest.mark.tag('describe', 'smoke')
def test_describe_with_column_filter_with_session(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1, 'Y': 1, 'Z': 1, '2D': 3}
    size = 100
    data = generate_df(['MD', 'X', 'Y', 'Z', '2D[0]', '2D[1]', '2D[2]'], range(size))
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        create_data_with_session(with_wdms_env, record_id, serializer, data, entity_type)

        validation_list = [  # tuple (params, expected_status, expected data)
            ({"curves": "MD"}, 200, data[['MD']]),
            ({"curves": "X, Y, Z"}, 200, data[['X', 'Y', 'Z']]),
            ({"curves": "W, X"}, 200, data[['X']]),
            ({"curves": "2D[0]"}, 200, data[['2D[0]']]),
            ({"curves": "2D[0:1]"}, 200, data[['2D[0]', '2D[1]']]),
            ({"curves": "2D"}, 200, data[['2D[0]', '2D[1]', '2D[2]']]),
            ({"curves": "Y, X"}, 200, data[['Y', 'X']]),  # filter order should be maintain
            ({"curves": "2D[1], 2D[0]"}, 200, data[['2D[1]', '2D[0]']]),  # filter order should be maintain
        ]

        for (params, expected_status, expected_data) in validation_list:
            headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}
            result = build_request_get_data_describe(entity_type, record_id
                                                     ).call(with_wdms_env,
                                                            params=params,
                                                            headers=headers,
                                                            assert_status=expected_status)
            if result.ok:
                res_as_dict = result.response.json()
                assert res_as_dict["numberOfRows"] == len(expected_data.index)
                assert res_as_dict["columns"] == expected_data.columns.tolist()
