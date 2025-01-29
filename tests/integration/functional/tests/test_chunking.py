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

import io
from contextlib import contextmanager
import random
from uuid import UUID

import numpy.testing as npt
import pandas as pd
import pytest
from typing import List

from ..generate_dataframe import generate_df

from .fixtures import with_wdms_env
from wdms_client.request_builders.wdms.crud.log import build_request_create_log, build_request_delete_log
from wdms_client.request_builders.wdms.session import build_delete_session
from wdms_client.request_runner import RequestRunner, Request

from wdms_client.request_builders.wdms.crud.osdu_welllog import (
    build_request_create_osdu_welllog,
    build_request_delete_osdu_welllog)

from wdms_client.request_builders.wdms.crud.osdu_wellboretrajectory import (
    build_request_create_osdu_wellboretrajectory,
    build_request_delete_osdu_wellboretrajectory)

entity_type_dict = {
    "well_log": {"entity": "welllogs", "version": "v3", "alpha-prefix": "ddms"},
    "wellbore_trajectory": {"entity": "wellboretrajectories", "version": "v3", "alpha-prefix": "ddms"},
    "log": {"entity": "logs", "version": "v2", "alpha-prefix": "alpha/ddms"},
}


def build_base_url(entity_type: str) -> str:
    return ('{{base_url}}/'+ f'{entity_type_dict[entity_type]["alpha-prefix"]}/'
            f'{entity_type_dict[entity_type]["version"]}/'
            f'{entity_type_dict[entity_type]["entity"]}')


@contextmanager
def create_record(env, entity_type: str, curves: List[str]):
    if entity_type == "well_log":
        result = build_request_create_osdu_welllog(False, curves).call(env)
    elif entity_type == "wellbore_trajectory":
        result = build_request_create_osdu_wellboretrajectory(False, curves).call(env)
    elif entity_type == "log":
        result = build_request_create_log().call(env)
    else:
        raise RuntimeError()

    result.assert_ok()
    resobj = result.get_response_obj()
    assert len(resobj.recordIds) == 1

    # TODO: when we have the version in the response must return as well
    record_id = resobj.recordIds[0]

    yield record_id

    # actually
    if entity_type == "well_log":
        build_request_delete_osdu_welllog(record_id).call(env)
    elif entity_type == "wellbore_trajectory":
        build_request_delete_osdu_wellboretrajectory(record_id).call(env)
    elif entity_type == "log":
        env.set('log_record_id', record_id)
        build_request_delete_log().call(env)


def build_request(name, method, url, *, payload=None, headers=None) -> RequestRunner:
    rq_proto = Request(
        name=name,
        method=method,
        url=url,
        headers={
            "data-partition-id": "{{data_partition}}",
            "Connection": "{{header_connection}}",
            "Authorization": "Bearer {{token}}",
        },
        payload=payload,
    )

    if headers:
        rq_proto.headers.update(headers)

    return RequestRunner(rq_proto)


def build_request_post_data(entity_type: str, record_id: str, payload) -> RequestRunner:
    url = build_base_url(entity_type) + f'/{record_id}/data'
    return build_request(f'{entity_type} post data', 'POST', url, payload=payload)

def build_request_post_data_without_dask(entity_type: str, record_id: str, payload) -> RequestRunner:
    url = build_base_url_without_dask(entity_type) + f'/{record_id}/data'
    return build_request(f'{entity_type} post data', 'POST', url, payload=payload)

def build_request_post_chunk(entity_type: str, record_id: str, session_id: UUID, payload) -> RequestRunner:
    url = build_base_url(entity_type) + f'/{record_id}/sessions/{session_id}/data'
    return build_request(f'{entity_type} post data', 'POST', url, payload=payload)

def build_request_get_data(entity_type: str, record_id: str, filters=None) -> RequestRunner:
    url = build_base_url(entity_type) + f'/{record_id}/data'
    if filters:
        url = url + '?' + '&'.join(f'{k}={v}' for k, v in filters.items())
    return build_request(f'{entity_type} get data', 'GET', url)


def create_session(env, entity_type: str, record_id: str, overwrite: bool) -> str:
    url = build_base_url(entity_type) + f'/{record_id}/sessions'
    runner = build_request(f'create {entity_type} session', 'POST', url,
                           payload={'mode': 'overwrite' if overwrite else 'update'})
    return runner.call(env, assert_status=200, headers={"Content-Type": "application/json"}).get_response_obj().id


def complete_session(env, entity_type: str, record_id: str, session_id: UUID, commit: bool):
    state = "commit" if commit else "abandon"
    url = build_base_url(entity_type) + f'/{record_id}/sessions/{session_id}'
    runner = build_request(f'{state} session', 'PATCH', url, payload={'state': state})
    runner.call(env, headers={"Content-Type": "application/json"}).assert_ok()


class ParquetSerializer:
    mime_type = 'application/x-parquet'

    def read(self, parquet_bytes):
        f = io.BytesIO(parquet_bytes)
        f.seek(0)
        return pd.read_parquet(f)

    def dump(self, df):
        return df.to_parquet(engine="pyarrow")


class JsonSerializer:
    mime_type = 'application/json'

    def read(self, json_content):
        f = io.BytesIO(json_content)
        f.seek(0)
        return pd.read_json(f, orient='split')

    def dump(self, df):
        return df.to_json(orient='split')


WELLLOG_URL_PREFIX = 'ddms/v3/welllogs'


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory", "log"])
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
def test_send_one_chunk_without_session(with_wdms_env, entity_type, serializer):
    col_and_nb_col = {'MD': 1, 'X': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        data = generate_df(col_and_nb_col.keys(), range(8))
        data_to_send = serializer.dump(data)
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()

        result = build_request_get_data(entity_type, record_id).call(with_wdms_env, headers=headers, assert_status=200)

        actual_df = serializer.read(result.response.content)
        actual_df.index.name = None
        pd.testing.assert_frame_equal(data, actual_df, check_dtype=False)
        # check type set to false since in Json dType is lost so int32 can become int64


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory", "log"])
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
def test_send_one_chunk_with_session_commit(with_wdms_env, entity_type, serializer):

    col_and_nb_col = {'MD': 1, 'X': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        expected = generate_df(col_and_nb_col.keys(), range(8))

        # create session
        session_id = create_session(with_wdms_env, entity_type, record_id, True)  # mode overwrite

        # post chunk
        build_request_post_chunk(
            entity_type, record_id, session_id, serializer.dump(expected)
        ).call(
            with_wdms_env, headers={'Content-Type': serializer.mime_type},
        ).assert_ok()

        # commit session
        complete_session(with_wdms_env, entity_type, record_id, session_id, True)  # commit

        # then read and check expected
        result = build_request_get_data(
            entity_type, record_id
        ).call(
            with_wdms_env, headers={'Accept': serializer.mime_type}, assert_status=200
        )
        actual = serializer.read(result.response.content)
        actual.index.name = None
        pd.testing.assert_frame_equal(expected, actual, check_dtype=False)
        # check type set to false since in Json dType is lost so int32 can become int64


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize("shuffle", [False])  # [False, True]
def test_send_multiple_chunks_with_session_commit(with_wdms_env, shuffle):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1, 'Y': 1, 'Z': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        data = generate_df(col_and_nb_col.keys(), range(1000))
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        # create session
        session_id = create_session(with_wdms_env, entity_type, record_id, True)  # mode overwrite

        # post a chunk
        chunks = [data.iloc[idx:idx + 100].to_parquet(engine="pyarrow") for idx in range(0, 1000, 100)]
        if shuffle:
            random.shuffle(chunks)  # chunk order should not matter

        for chunk in chunks:
            build_request_post_chunk(
                entity_type, record_id, session_id, chunk
            ).call(
                with_wdms_env, headers=headers,
            ).assert_ok()

        # commit session
        complete_session(with_wdms_env, entity_type, record_id, session_id, True)

        # check full dataframe
        result = build_request_get_data(
            entity_type, record_id
        ).call(with_wdms_env, headers=headers, assert_status=200)
        pd.testing.assert_frame_equal(data, serializer.read(result.response.content))

        # check per columns
        for col in data.columns:
            result = build_request_get_data(
                entity_type, record_id
            ).call(with_wdms_env, headers=headers, params={'curves': col}, assert_status=200)
            cmp_data = serializer.read(result.response.content)
            assert cmp_data.columns == [col]
            npt.assert_array_almost_equal(data[col], cmp_data[col])


@pytest.mark.tag('chunking', 'smoke')
def test_get_data_with_offset_filter(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1}
    with create_record(with_wdms_env, entity_type,col_and_nb_col) as record_id:
        size = 100
        data = generate_df(col_and_nb_col.keys(), range(size))
        data_to_send = serializer.dump(data)
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        # post data
        build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()

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
            r = build_request_get_data(
                entity_type, record_id
            ).call(with_wdms_env, headers=headers, params=params, assert_status=expected_status)

            if r.ok:
                actual_df = serializer.read(r.response.content)
                actual_df.index.name = None
                pd.testing.assert_frame_equal(expected_data, actual_df)


@pytest.mark.tag('chunking', 'smoke')
def test_get_data_with_column_filter(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1, 'Y': 1, 'Z': 1, '2D': 3}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        size = 100
        data = generate_df(['MD', 'X', 'Y', 'Z', '2D[0]', '2D[1]', '2D[2]'], range(size))
        data_to_send = serializer.dump(data)
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        # post data
        build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()

        validation_list = [  # tuple (params, expected_status, expected data)
            ({"curves": "MD"}, 200, data[['MD']]),
            ({"curves": "X, Y, Z"}, 200, data[['X', 'Y', 'Z']]),
            ({"curves": "W, X"}, 404, data[['X']]),
            ({"curves": "2D[0]"}, 200, data[['2D[0]']]),
            ({"curves": "2D[0:1]"}, 200, data[['2D[0]', '2D[1]']]),
            ({"curves": "2D"}, 200, data[['2D[0]', '2D[1]', '2D[2]']]),
            ({"curves": "Y, X"}, 200, data[['Y', 'X']]),  # filter order should be maintain
            ({"curves": "2D[1], 2D[0]"}, 200, data[['2D[1]', '2D[0]']]),  # filter order should be maintain
        ]

        for (params, expected_status, expected_data) in validation_list:
            r = build_request_get_data(
                entity_type, record_id
            ).call(with_wdms_env, headers=headers, params=params, assert_status=expected_status)

            if r.ok:
                actual_df = serializer.read(r.response.content)
                actual_df.index.name = None
                pd.testing.assert_frame_equal(expected_data, actual_df)


@pytest.mark.tag('chunking', 'smoke')
def test_get_data_with_limit_filter(with_wdms_env):
    # well log on parquet
    entity_type = "well_log"
    serializer = ParquetSerializer()

    col_and_nb_col = {'MD': 1, 'X': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        size = 100
        data = generate_df(col_and_nb_col.keys(), range(size))
        data_to_send = serializer.dump(data)
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        # post data
        build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()

        validation_list = [  # tuple (params, expected_status, expected data)
            ({"limit": 1}, 200, data.head(1)),
            ({"limit": 50}, 200, data.head(50)),
            ({"limit": 99}, 200, data.head(99)),
            ({"limit": "3"}, 200, data.head(3)),
            ({"limit": 50, "curves": "X"}, 200, data[['X']].head(50)),
            ({"limit": 100}, 200, data),
            ({"limit": 150}, 200, data),
            # invalid limit
            ({"limit": 0}, 422, None),
            ({"limit": -2}, 422, None)
        ]

        for (params, expected_status, expected_data) in validation_list:
            r = build_request_get_data(
                entity_type, record_id
            ).call(with_wdms_env, headers=headers, params=params, assert_status=expected_status)

            if r.ok:
                actual_df =  serializer.read(r.response.content)
                actual_df.index.name = None
                pd.testing.assert_frame_equal(expected_data, actual_df)


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory", "log"])
def test_get_data_with_limit_and_offset_filter(with_wdms_env, entity_type):
    serializer = ParquetSerializer()
    col_and_nb_col = {'MD': 1, 'X': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        size = 100
        data = generate_df(col_and_nb_col.keys(), range(size))
        data_to_send = serializer.dump(data)
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        # post data
        build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()

        validation_list = [  # tuple (params, expected_status, expected data)
            ({"limit": 5, "offset": 2}, 200, data.tail(size-2).head(5)),
            ({"limit": 5, "offset": size-2}, 200, data.tail(size-(size-2)).head(5))
        ]

        for (params, expected_status, expected_data) in validation_list:
            r = build_request_get_data(
                entity_type, record_id
            ).call(with_wdms_env, headers=headers, params=params, assert_status=expected_status)

            if r.ok:
                pd.testing.assert_frame_equal(expected_data, serializer.read(r.response.content))


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory", "log"])
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
def test_multiple_overwrite_sessions_in_parallel_then_commit(with_wdms_env, entity_type, serializer):
    col_and_nb_col = {'MD': 1, 'X': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        # create session
        sessions = [{
            'id': create_session(with_wdms_env, entity_type, record_id, True),
            'df': generate_df(col_and_nb_col.keys(), range(8))
        } for _i in range(5)]  # mode overwrite

        for session in sessions:
            session_id = session['id']
            expected = session['df']
            # post chunk
            build_request_post_chunk(entity_type, record_id, session_id, serializer.dump(expected)).call(
                with_wdms_env, headers={'Content-Type': serializer.mime_type},).assert_ok()

        random.shuffle(sessions) 

        for session in sessions:
            session_id = session['id']
            expected = session['df']

            # commit session
            complete_session(with_wdms_env, entity_type, record_id, session_id, True)  # commit

            # then read and check expected
            result = build_request_get_data(entity_type, record_id).call(
                with_wdms_env, headers={'Accept': serializer.mime_type}, assert_status=200)

            actual = serializer.read(result.response.content)
            # for performance reason, dataframe provided may have a named index, it doesn't matter but make the assert
            # dataframe equals to fail, just remove it
            actual.index.name = None
            pd.testing.assert_frame_equal(
                expected, actual,  check_dtype=False)
            # check type set to false since in Json dType is lost so int32 can become int64


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory", "log"])
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
def test_multiple_update_sessions_in_parallel_then_commit(with_wdms_env, entity_type, serializer):

    col_and_nb_col = {'MD': 1, 'X': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        # post data
        data = generate_df(col_and_nb_col.keys(), range(10))
        data_to_send = serializer.dump(data)
        build_request_post_data(entity_type, record_id, data_to_send).call(
            with_wdms_env, headers={'Content-Type': serializer.mime_type}).assert_ok()

        # create session
        sessions = [{
            'id': create_session(with_wdms_env, entity_type, record_id, False),
            'df': generate_df(col_and_nb_col.keys(), range(10, 20))
        } for _i in range(5)]  # mode overwrite

        for session in sessions:
            session_id = session['id']
            expected = session['df']
            # post chunk
            build_request_post_chunk(entity_type, record_id, session_id, serializer.dump(expected)).call(
                with_wdms_env, headers={'Content-Type': serializer.mime_type},).assert_ok()

        random.shuffle(sessions) 

        for session in sessions:
            session_id = session['id']
            expected = pd.concat([data, session['df']])

            # commit session
            complete_session(with_wdms_env, entity_type, record_id, session_id, True)  # commit

            # then read and check expected
            result = build_request_get_data(entity_type, record_id).call(
                with_wdms_env, headers={'Accept': serializer.mime_type}, assert_status=200)

            pd.testing.assert_frame_equal(
                expected, serializer.read(result.response.content), check_dtype=False)
            # check type set to false since in Json dType is lost so int32 can become int64


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log", "wellbore_trajectory"])
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
def test_send_arrayd_without_session(with_wdms_env, entity_type, serializer):
    col_and_nb_col = {'MD': 1, 'array_10_A': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        data = generate_df(col_and_nb_col.keys(), range(8))
        data_to_send = serializer.dump(data)
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()

        result = build_request_get_data(entity_type, record_id).call(with_wdms_env, headers=headers, assert_status=200)
        actual_df = serializer.read(result.response.content)
        actual_df.index.name = None
        pd.testing.assert_frame_equal(data, actual_df, check_dtype=False)


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize('entity_type', ["well_log"])
@pytest.mark.parametrize('serializer', [ParquetSerializer()])
def test_describe(with_wdms_env, entity_type, serializer):
    col_and_nb_col = {'BOB': 1, 'MD': 1}
    with create_record(with_wdms_env, entity_type, col_and_nb_col) as record_id:
        number_of_rows = 8
        data = generate_df(col_and_nb_col.keys(), range(number_of_rows))
        data_to_send = serializer.dump(data)
        headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

        build_request_post_data(entity_type, record_id, data_to_send).call(with_wdms_env, headers=headers).assert_ok()

        result = build_request_get_data(entity_type, record_id, {'describe': True}).call(with_wdms_env, headers=headers, assert_status=200)
        res = result.response.json()
        assert res['numberOfRows'] == number_of_rows
        assert res['columns'] == ['BOB', 'MD']
