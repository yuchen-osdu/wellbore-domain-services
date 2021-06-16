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
import random

import httpx
import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from ..request_builders.wdms.session import build_delete_session
from .fixtures import with_wdms_env
from .test_session import SESSION_URL_PREFIX, create_session, with_welllog


def generate_df(columns, index):
    nbrows = len(index)
    df = pd.DataFrame(
        np.random.randint(-100, 1000, size=(nbrows, len(columns))), index=index)
    df.columns = columns
    return df


def get_client(with_wdms_env):
    return httpx.Client(
        base_url=with_wdms_env.get('base_url'),
        verify=False,
        headers={
            "data-partition-id": with_wdms_env.get('data_partition'),
            "Authorization": f"Bearer {with_wdms_env.get('token')}",
        },
        timeout=120
    )


def read_parquet(parquet_bytes):
    f = io.BytesIO(parquet_bytes)
    f.seek(0)
    return pd.read_parquet(f)


WELLLOG_URL_PREFIX = 'alpha/ddms/v3/welllogs'


# todo get data json

@pytest.mark.tag('chunking', 'smoke')
def test_send_one_chunk_without_session(with_wdms_env, with_welllog):
    record_id = with_welllog
    data_url = f'/{WELLLOG_URL_PREFIX}/{record_id}/data'

    # Send data in parquet format
    data = generate_df(['MD', 'X'], range(8))
    data_to_send = data.to_parquet(engine="pyarrow")
    headers = {
        'content-type': 'application/x-parquet',
        "Accept": 'application/x-parquet'
    }
    with get_client(with_wdms_env) as client:
        res = client.post(data_url, content=data_to_send, headers=headers)
        assert res.status_code == httpx.codes.OK
        res = client.get(data_url, headers=headers)
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data, read_parquet(res.content))


@pytest.mark.tag('chunking', 'smoke')
def test_send_one_chunk_with_session_commit(with_wdms_env, with_welllog):
    record_id = with_welllog

    # Send data in parquet format
    data = generate_df(['MD', 'X'], range(8))
    data_to_send = data.to_parquet(engine="pyarrow")
    headers = {
        'content-type': 'application/x-parquet',
        "Accept": 'application/x-parquet'
    }

    with get_client(with_wdms_env) as client:
        # create an update session
        res = client.post(f'/{WELLLOG_URL_PREFIX}/{record_id}/sessions', json={'mode': 'overwrite'})
        assert res.status_code == httpx.codes.OK, f'{res.request.method} : {res.url} -> {res.status_code}'
        session = res.json()
        session_id = session['id']

        # post a chunk
        res = client.post(f'/{WELLLOG_URL_PREFIX}/{record_id}/sessions/{session_id}/data', content=data_to_send, headers=headers)
        assert res.status_code == httpx.codes.OK

        res = client.patch(f'/{WELLLOG_URL_PREFIX}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
        assert res.status_code == httpx.codes.OK

        # get and check chunk
        res = client.get(f'/{WELLLOG_URL_PREFIX}/{record_id}/data', headers=headers)
        assert res.status_code == httpx.codes.OK
        cmp_data = read_parquet(res.content)
        pd.testing.assert_frame_equal(data, cmp_data)


@pytest.mark.tag('chunking', 'smoke')
@pytest.mark.parametrize("shuffle", [False, True])
def test_send_multiple_chunks_with_session_commit(with_wdms_env, with_welllog, shuffle):
    record_id = with_welllog
    
    # Send data in parquet format
    data = generate_df(['MD', 'X', 'Y', 'Z'], range(1000))
    headers={
        'content-type':'application/x-parquet',
        "Accept": 'application/x-parquet'
    }

    with get_client(with_wdms_env) as client:
        # create an update session
        res = client.post(f'/{WELLLOG_URL_PREFIX}/{record_id}/sessions', json={'mode': 'overwrite'})
        assert res.status_code == httpx.codes.OK, f'{res.request.method} : {res.url} -> {res.status_code}'
        session = res.json()
        session_id = session['id']

        # post a chunk
        chunks = [data.iloc[idx:idx+100].to_parquet(engine="pyarrow") for idx in range(0, 1000, 100)]
        if shuffle:
            random.shuffle(chunks) # chunk order should not mattter 
        for chunk in chunks:
            res = client.post(f'/{WELLLOG_URL_PREFIX}/{record_id}/sessions/{session_id}/data', content=chunk, headers=headers)
            assert res.status_code == httpx.codes.OK

        res = client.patch(f'/{WELLLOG_URL_PREFIX}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
        assert res.status_code == httpx.codes.OK

        # get and check chunk
        res = client.get(f'/{WELLLOG_URL_PREFIX}/{record_id}/data', headers=headers)
        assert res.status_code == httpx.codes.OK
        cmp_data = read_parquet(res.content)
        pd.testing.assert_frame_equal(data, cmp_data)

        # get and check per columns
        for col in data.columns:
            res = client.get(f'/{WELLLOG_URL_PREFIX}/{record_id}/data', params={'curves': col}, headers=headers)
            assert res.status_code == httpx.codes.OK
            cmp_data = read_parquet(res.content)
            assert cmp_data.columns == [col]
            npt.assert_array_almost_equal(data[col], cmp_data[col])


@pytest.mark.tag('chunking', 'smoke')
def test_get_data_with_offset_filter(with_wdms_env, with_welllog):
    record_id = with_welllog
    data_url = f'/{WELLLOG_URL_PREFIX}/{record_id}/data'

    # Send data in parquet format
    size = 100
    data = generate_df(['MD', 'X'], range(size))
    data_to_send = data.to_parquet(engine="pyarrow")
    headers = {
        'content-type': 'application/x-parquet',
        "Accept": 'application/x-parquet'
    }
    with get_client(with_wdms_env) as client:
        # send data
        res = client.post(data_url, content=data_to_send, headers=headers)
        assert res.status_code == httpx.codes.OK

        # read data
        res = client.get(data_url, headers=headers, params={"offset": 0})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data, read_parquet(res.content))
        
        res = client.get(data_url, headers=headers, params={"offset": "0"})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data, read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"offset": 1})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.tail(size-1), read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"offset": int(size/2)})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.tail(int(size/2)), read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"offset": size-1})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.tail(1), read_parquet(res.content))

        # with column filter
        res = client.get(data_url, headers=headers, params={"offset": 1, "curves": "X"})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data[['X']].tail(size-1), read_parquet(res.content))

        # if offset >= number of rows, returns an empty dataFrame with columns
        res = client.get(data_url, headers=headers, params={"offset": size})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.tail(0), read_parquet(res.content))
        res = client.get(data_url, headers=headers, params={"offset": size + 50})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.tail(0), read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"offset": -2})
        assert res.status_code == httpx.codes.UNPROCESSABLE_ENTITY
        res = client.get(data_url, headers=headers, params={"offset": "false"})
        assert res.status_code == httpx.codes.UNPROCESSABLE_ENTITY


@pytest.mark.tag('chunking', 'smoke')
def test_get_data_with_column_filter(with_wdms_env, with_welllog):
    record_id = with_welllog
    data_url = f'/{WELLLOG_URL_PREFIX}/{record_id}/data'

    # Send data in parquet format
    size = 100
    data = generate_df(['MD', 'X', 'Y', 'Z'], range(size))
    data_to_send = data.to_parquet(engine="pyarrow")
    headers = {
        'content-type': 'application/x-parquet',
        "Accept": 'application/x-parquet'
    }
    with get_client(with_wdms_env) as client:
        # send data
        res = client.post(data_url, content=data_to_send, headers=headers)
        assert res.status_code == httpx.codes.OK

        res = client.get(data_url, headers=headers, params={"curves": "MD"})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data[['MD']], read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"curves": "X, Y, Z"})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data[['X', 'Y', 'Z']], read_parquet(res.content))

        "ignore with non existing column"
        res = client.get(data_url, headers=headers, params={"curves": "W, X"})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data[['X']], read_parquet(res.content))


@pytest.mark.tag('chunking', 'smoke')
def test_get_data_with_limit_filter(with_wdms_env, with_welllog):
    record_id = with_welllog
    data_url = f'/{WELLLOG_URL_PREFIX}/{record_id}/data'

    # Send data in parquet format
    size = 100
    data = generate_df(['MD', 'X'], range(size))
    data_to_send = data.to_parquet(engine="pyarrow")
    headers = {
        'content-type': 'application/x-parquet',
        "Accept": 'application/x-parquet'
    }
    with get_client(with_wdms_env) as client:
        # send data
        res = client.post(data_url, content=data_to_send, headers=headers)
        assert res.status_code == httpx.codes.OK

        # read data
        res = client.get(data_url, headers=headers, params={"limit": 0})
        assert res.status_code == httpx.codes.UNPROCESSABLE_ENTITY
        res = client.get(data_url, headers=headers, params={"limit": -2})
        assert res.status_code == httpx.codes.UNPROCESSABLE_ENTITY

        res = client.get(data_url, headers=headers, params={"limit": 1})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.head(1), read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"limit": 50})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.head(50), read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"limit": 99})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.head(99), read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"limit": "3"})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.head(3), read_parquet(res.content))

        # with column filter
        res = client.get(data_url, headers=headers, params={"limit": 50, "curves": "X"})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data[['X']].head(50), read_parquet(res.content))

        # if limit >= number of rows, returns all rows
        res = client.get(data_url, headers=headers, params={"limit": 100})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data, read_parquet(res.content))
        res = client.get(data_url, headers=headers, params={"limit": 150})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data, read_parquet(res.content))


@pytest.mark.tag('chunking', 'smoke')
def test_get_data_with_limit_and_offset_filter(with_wdms_env, with_welllog):
    record_id = with_welllog
    data_url = f'/{WELLLOG_URL_PREFIX}/{record_id}/data'

    # Send data in parquet format
    size = 100
    data = generate_df(['MD', 'X'], range(size))
    data_to_send = data.to_parquet(engine="pyarrow")
    headers = {
        'content-type': 'application/x-parquet',
        "Accept": 'application/x-parquet'
    }
    with get_client(with_wdms_env) as client:
        # send data
        res = client.post(data_url, content=data_to_send, headers=headers)
        assert res.status_code == httpx.codes.OK

        # read data
        res = client.get(data_url, headers=headers, params={"limit": 5, "offset": 2})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.tail(size-2).head(5), read_parquet(res.content))

        res = client.get(data_url, headers=headers, params={"limit": 5, "offset": size-2})
        assert res.status_code == httpx.codes.OK
        pd.testing.assert_frame_equal(data.tail(size-(size-2)).head(5), read_parquet(res.content))
