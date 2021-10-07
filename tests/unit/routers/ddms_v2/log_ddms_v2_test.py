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
tests specific to logset APIs. Common tests implemented in common_ddms_v2_test
"""

import asyncio
import json
from tempfile import TemporaryDirectory
from io import BytesIO

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from fastapi import HTTPException, Header
from fastapi.testclient import TestClient
import pytest

from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from odes_storage.models import Record, CreateUpdateRecordsResponse

from app.clients.storage_service_blob_storage import StorageRecordServiceBlobStorage
from app.helper import traces
from app.auth.auth import require_opendes_authorized_user
from app.middleware import require_data_partition_id
from app.model.log_bulk import LogBulkHelper
from app.bulk_persistence import MimeTypes
from app.utils import Context
from app.wdms_app import wdms_app, app_injector
from app.clients import *
from tests.unit.test_utils import assert_dict_contained, make_record, nope_logger_fixture

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


class TestHelper:
    DATA_PARTITION_ID = 'test_partition'
    BASE_HEADERS = {'data-partition-id': DATA_PARTITION_ID}
    URL_PREFIX = '/ddms/v2'

    @staticmethod
    def build_url(path: str):
        return TestHelper.URL_PREFIX + path

    @staticmethod
    def get_record_from_storage(record_id):
        async def _fetcher(_id):
            storage: StorageRecordServiceClient = await app_injector.get(StorageRecordServiceClient)
            return await storage.get_record(_id, TestHelper.DATA_PARTITION_ID)

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_fetcher(record_id))

    @staticmethod
    def post_record_to_storage(one_record_or_list_of_records):
        """ return one id it single record else list of ids """

        async def _putter(record_or_list):
            records = record_or_list if type(record_or_list) == list else [record_or_list]
            storage: StorageRecordServiceClient = await app_injector.get(StorageRecordServiceClient)
            response = await storage.create_or_update_records(record=records,
                                                              data_partition_id=TestHelper.DATA_PARTITION_ID)
            ids = response.record_ids
            return ids if type(record_or_list) == list else ids[0]

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_putter(one_record_or_list_of_records))

    @staticmethod
    def make_minimal_log_dict(name: str, id: str = None) -> dict:
        return TestHelper.make_minimal_log_record(name, id).dict()

    @staticmethod
    def make_minimal_log_record(name: str, id: str = None) -> Record:
        record = make_record()
        record.data = {"log": {"name": name}}

        if id:
            record.id = id
        return record

    @staticmethod
    def get_bulk_id_from_record(record) -> str:
        return LogBulkHelper.get_bulk_id(record)


@pytest.fixture
def client(nope_logger_fixture):
    with TemporaryDirectory() as tmpdir:
        async def storage_service_builder(*args, **kwargs):
            return StorageRecordServiceBlobStorage(LocalFSBlobStorage(directory=tmpdir), 'p1', 'c1')

        async def blob_storage_builder(*args, **kwargs):
            return LocalFSBlobStorage(directory=tmpdir)

        async def set_default_partition(data_partition_id: str = Header('opendes')):
            Context.set_current_with_value(partition_id=data_partition_id)

        app_injector.register(BlobStorageBase, blob_storage_builder)
        app_injector.register(StorageRecordServiceClient, storage_service_builder)

        async def do_nothing():
            # empty method
            pass

        wdms_app.dependency_overrides[require_opendes_authorized_user] = do_nothing
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition

        yield TestClient(wdms_app)

        wdms_app.dependency_overrides = {}  # clean up


log_data = [
    pytest.param([[2.0, 10.1], [2.2, 20.1], [2.4, 30.1], [2.6, 40.]], id="double"),
    pytest.param([[2.0, 10.1], [2.2, 20.1], [2.4, np.NaN], [2.6, 40.1]], id="double with nan"),
    pytest.param([[2.0, [1.0, 10.0]], [2.2, [2.0, 20.0]], [2.4, [3.0, 30.0]], [2.6, [4.0, 40.0]]], id="double array"),
    pytest.param([[2.0, [1.0, 10.0]], [2.2, np.NaN], [2.4, [2.0, 20.0]], [2.6, [3.0, 30.0]]],
                 id="double array with nan"),
    pytest.param([[2.0, "ZONE 1"], [2.2, "Zone 2"], [2.4, "ZONE 3"], [2.6, "ZONE 4"]], id="text"),
    pytest.param([[2.0, "ZONE 1"], [2.2, np.NaN], [2.4, "ZONE 2"], [2.6, "ZONE 3"]], id="text with nan"),
    pytest.param([[2.0, ["ZONE 1", "AAA"]], [2.2, ["ZONE 2", "BBB"]], [2.4, ["ZONE 3", ]]], id="text array"),
    pytest.param([[2.0, ["ZONE 1", "AAA"]], [2.2, np.NaN], [2.4, ["ZONE 3", ]]], id="text array with NaN"),
    pytest.param([[2.4, 10.1], [2.2, 20.1], [2.0, 30.1]], id="decreasing index"),
    pytest.param([[2.4, 10.1], [2.3, np.NaN], [2.2, 20.], [2.0, 30.1]], id="decreasing index with nan"),
    pytest.param([[2.0, 10.1], [1.8, 20.1], [1.8, 20.1], [2.0, 30.1]], id="duplicate index"),
    pytest.param([[2.0, 10.1], [1.8, 20.1], [1.8, np.NaN], [2.0, 30.1]], id="duplicate index with nan"),
]
log_data_orient = 'split'


def logs_write(client, test_data, nan_conversion):
    # given
    log_id = '1337'
    record = TestHelper.make_minimal_log_record('test_logs_write_data_log', id=log_id)
    TestHelper.post_record_to_storage(record)
    df = pd.DataFrame(test_data)
    content = df
    if nan_conversion:
        content = content.fillna("NaN")
    json_content = content.to_json(orient=log_data_orient)
    byte_stream = BytesIO(str.encode(json_content))
    # when WRITE ----------------------------------------------------------
    response = client.post(TestHelper.build_url(f'/logs/{log_id}/upload_data?orient=' + log_data_orient),
                          files={'file': ('test_file_data.json', byte_stream, 'application/json')},
                          headers=TestHelper.BASE_HEADERS)
    return log_id, df, response, client


@pytest.mark.parametrize("nan_conversion", [pytest.param(True, id="nan_string"),
                                            pytest.param(False, id="native_nan")])
@pytest.mark.parametrize("test_data", log_data)
def test_logs_write_then_read_data(client, test_data, nan_conversion):
    log_id, df, response, client = logs_write(client, test_data, nan_conversion)

    # then
    assert response.status_code == 200
    store_response = CreateUpdateRecordsResponse.parse_raw(response.content)
    assert store_response.record_count == 1
    assert store_response.record_ids[0] == log_id

    # check
    actual = TestHelper.get_record_from_storage(log_id)
    bulk_id = TestHelper.get_bulk_id_from_record(actual)
    assert bulk_id

    # when READ -----------------------------------------------------------
    response = client.get(TestHelper.build_url(f'/logs/{log_id}/data?orient=' + log_data_orient),
                          headers=TestHelper.BASE_HEADERS)

    data = response.content
    actual_df = pd.read_json(data, orient=log_data_orient).replace("NaN", np.NaN)
    pd.testing.assert_frame_equal(df, actual_df)


@pytest.mark.parametrize("nan_conversion", [pytest.param(True, id="nan_string"),
                                            pytest.param(False, id="native_nan")])
@pytest.mark.parametrize("test_data", log_data)
def test_logs_write_then_read_data_statistics(client, test_data, nan_conversion):
    log_id, df, response, client = logs_write(client, test_data, nan_conversion)

    # when READ -----------------------------------------------------------
    response = client.get(TestHelper.build_url(f'/logs/{log_id}/statistics'),
                          headers=TestHelper.BASE_HEADERS)

    df_stat = df.describe(include="all").to_json()
    data = response.json()
    actual_df_stat = pd.DataFrame(data).to_json()
    assert df_stat == actual_df_stat


@pytest.mark.parametrize("nan_conversion", [pytest.param(True, id="nan_string"),
                                            pytest.param(False, id="native_nan")])
@pytest.mark.parametrize("test_data", log_data)
def test_logs_upload_file_then_read_data(client, test_data, nan_conversion):

    log_id, df, response, client = logs_write(client, test_data, nan_conversion)

    # then
    assert response.status_code == 200
    store_response = CreateUpdateRecordsResponse.parse_raw(response.content)
    assert store_response.record_count == 1
    assert store_response.record_ids[0] == log_id

    # check
    actual = TestHelper.get_record_from_storage(log_id)
    bulk_id = TestHelper.get_bulk_id_from_record(actual)
    assert bulk_id

    # when READ -----------------------------------------------------------
    response = client.get(TestHelper.build_url(f'/logs/{log_id}/data?orient=' + log_data_orient),
                          headers=TestHelper.BASE_HEADERS)

    data = response.content
    actual_df = pd.read_json(data, orient=log_data_orient).replace("NaN", np.NaN)
    pd.testing.assert_frame_equal(df, actual_df)


@pytest.mark.parametrize("df", [
    pd.DataFrame([[1, [1, 4]], [2, [2, 5]], [3, [3, 6]]]),
    pd.DataFrame({'ref': range(100_000), 'values': [float(val) + 0.1 for val in range(100_000)]})
])
def test_logs_upload_parquet_read_json(client, df):
    # given
    record = TestHelper.make_minimal_log_record('test_logs_upload_parquet_read_json', id='1337')
    TestHelper.post_record_to_storage(record)

    buffer = BytesIO()
    pq.write_table(pa.Table.from_pandas(df), buffer, compression='none')
    buffer.seek(0)

    # when WRITE ----------------------------------------------------------
    response = client.post(TestHelper.build_url('/logs/1337/upload_data?orient=' + log_data_orient),
                           files={'file': ('test_file_data.parquet', buffer, MimeTypes.PARQUET.type)},
                           headers=TestHelper.BASE_HEADERS)

    # then
    assert response.status_code == 200
    store_response = CreateUpdateRecordsResponse.parse_raw(response.content)
    assert store_response.record_count == 1
    assert store_response.record_ids[0] == '1337'

    # check
    actual = TestHelper.get_record_from_storage('1337')
    bulk_id = TestHelper.get_bulk_id_from_record(actual)
    assert bulk_id

    # when READ -----------------------------------------------------------
    response = client.get(TestHelper.build_url('/logs/1337/data?orient=' + log_data_orient),
                          headers=TestHelper.BASE_HEADERS)

    data = response.content
    actual_df = pd.read_json(data, orient=log_data_orient).replace("NaN", np.NaN)
    pd.testing.assert_frame_equal(df, actual_df)


@pytest.mark.parametrize("nan_conversion", [pytest.param(True, id="nan_string"),
                                            pytest.param(False, id="native_nan")])
@pytest.mark.parametrize("test_data", log_data)
def test_logs_write_twice_then_read_data(client, test_data, nan_conversion):
    # given
    record = TestHelper.make_minimal_log_record('test_logs_write_twice_then_read_data', id='1337')
    TestHelper.post_record_to_storage(record)

    initial_df = pd.DataFrame(test_data)
    initial_df_json = initial_df
    if nan_conversion:
        initial_df_json = initial_df_json.fillna("NaN")
    initial_df_json = initial_df_json.to_json(orient='split')

    # when WRITE twice ----------------------------------------------------------
    client.post(TestHelper.build_url('/logs/1337/data?orient=' + log_data_orient),
               initial_df_json,
               headers=TestHelper.BASE_HEADERS)

    client.post(TestHelper.build_url('/logs/1337/data?orient=' + log_data_orient),
               initial_df_json,
               headers=TestHelper.BASE_HEADERS)

    # when READ -----------------------------------------------------------
    response = client.get(TestHelper.build_url('/logs/1337/data?orient=' + log_data_orient), headers=TestHelper.BASE_HEADERS)

    assert response.status_code == 200
    data = response.content
    actual_df = pd.read_json(data, orient=log_data_orient).replace("NaN", np.NaN)
    pd.testing.assert_frame_equal(initial_df, actual_df)


def double_frame_with_nan():
    df = pd.DataFrame(np.linspace(20., 40., 50))
    x = pd.DataFrame(10 * np.cos(np.linspace(20., 40., 50)))
    x = x.mask(x > 8.)
    df[1] = x
    return df


def decreasing_index_with_nan():
    df = pd.DataFrame({0: np.linspace(40., 20., 50),
                       1: 10 * np.cos(np.linspace(20., 40., 50))})
    x = pd.DataFrame(10 * np.cos(np.linspace(20., 40., 50)))
    x = x.mask(x > 8.)
    df[1] = x
    return df


def duplicate_index():
    df = pd.concat([pd.DataFrame(np.linspace(20., 35., 25)), pd.DataFrame(np.linspace(35., 50., 25))])
    x = pd.DataFrame(10 * np.cos(np.linspace(20., 40., 50)))
    df[1] = x
    return df


def duplicate_index_with_nan():
    df = pd.concat([pd.DataFrame(np.linspace(20., 35., 25)), pd.DataFrame(np.linspace(35., 50., 25))])
    x = pd.DataFrame(10 * np.cos(np.linspace(20., 40., 50)))
    x = x.mask(x > 8.)
    df[1] = x
    return df


decimated_log_data = [
    pytest.param(pd.DataFrame({0: np.linspace(20., 40., 50),
                               1: 10 * np.cos(np.linspace(20., 40., 50))}),
                 pd.DataFrame([[20.8163265306, -3.2441897554], [22.8571428571, -5.4493543395],
                               [24.8979591837, 8.1802597798], [26.9387755102, -1.9603923158],
                               [28.9795918367, -6.4045202806], [31.0204081633, 7.7616595133],
                               [33.0612244898, -0.6260548071], [35.1020408163, -7.1945739149],
                               [37.1428571429, 7.1429590909], [39.1836734694, 0.7244227635]]),
                 None, None, 10, id="double - 10 quantiles - no start and stop"),
    pytest.param(pd.DataFrame({0: np.linspace(20., 40., 50),
                               1: 10 * np.cos(np.linspace(20., 40., 50))}),
                 pd.DataFrame([[24.0816326531, 4.176987118], [25.9183673469, 6.3540531412],
                               [27.5510204081, -6.7375832739], [29.1836734694, -5.5210547907],
                               [30.8163265307, 7.4201766234], [32.4489795918, 4.6036642907],
                               [34.0816326531, -7.9893487738], [35.7142857142, -3.6159044249],
                               [37.3469387756, 8.4363996374], [39.1836734694, 0.7244227635]]),
                 23., 47., 10, id="double - 10 quantiles"),
    pytest.param(pd.DataFrame({0: np.linspace(20., 40., 50),
                               1: 10 * np.cos(np.linspace(20., 40., 50))}),
                 pd.DataFrame([[25.9183673469, 0.6992074799], [31.6326530612, 0.9659168348],
                               [37.3469387755, 0.9283513371]]),
                 23., 47., 3, id="double - 3 quantiles"),
    pytest.param(double_frame_with_nan(),
                 pd.DataFrame([[25.9183673469, -2.61463028], [31.6326530612, -1.3483568721],
                               [37.3469387755, -1.3681570385]]),
                 23., 47., 3, id="double - 3 quantiles"),
    # Note: apparently pandas does not preserve row order when using groupby.
    # That should not be an issue.
    pytest.param(pd.DataFrame({0: np.linspace(40., 20., 50),
                               1: 10 * np.cos(np.linspace(20., 40., 50))}),
                 pd.DataFrame([[24.0816326531, -1.7529330587], [25.9183673469, -7.9893487738],
                               [27.5510204082, 4.6036642907], [29.1836734693, 7.4201766234],
                               [30.8163265306, -5.5210547907], [32.4489795918, -6.7375832739],
                               [34.0816326531, 6.3540531412], [35.7142857142, 5.9520025144],
                               [37.3469387756, -7.0899265361], [39.1836734694, -3.2441897554]]),
                 47., 23., 10, id="decreasing index - 10 quantiles"),
    pytest.param(pd.DataFrame({0: np.linspace(40., 20., 50),
                               1: 10 * np.cos(np.linspace(20., 40., 50))}),
                 pd.DataFrame([[25.9183673469, -0.8791573344], [31.6326530612, -0.9847789041],
                               [37.3469387755, -0.7801838536]]),
                 47., 23., 3, id="decreasing index - 3 quantiles"),
    pytest.param(decreasing_index_with_nan(),
                 pd.DataFrame([[24.0816326531, -1.7529330587], [25.9183673469, -7.9893487738],
                               [27.5510204082, 3.0956886966], [29.1836734693, 5.226768143],
                               [30.8163265306, -5.5210547907], [32.4489795918, -6.7375832739],
                               [34.0816326531, 3.6049946383], [35.7142857142, 3.0395129137],
                               [37.3469387756, -7.0899265361], [39.1836734694, -3.2441897554]]),
                 47., 23., 10, id="decreasing index with nan - 10 quantiles"),
    pytest.param(decreasing_index_with_nan(),
                 pd.DataFrame([[25.9183673469, -2.6195828582], [31.6326530612, -2.6142522246],
                               [37.3469387755, -3.5001480995]]),
                 47., 23., 3, id="decreasing index with nan - 3 quantiles"),
    # It is not sure the decimation behavior with index that has duplicated indexes is the one expected for directional wells
    # Right now pandas will average based on the index value even if there are other index values in-between
    # we could reconsider it if there is a need with a precise requirement
    pytest.param(duplicate_index(),
                 pd.DataFrame([[24.0625, -7.0899265361], [26.5625, 5.9520025144],
                               [29.0625, 6.3540531412], [31.5625, -6.7375832739],
                               [34.25, -3.6006797089], [36.25, -3.6458372785],
                               [38.4375, -8.7002223092], [40.9375, 2.7898212287],
                               [43.4375, 8.3553039034], [45.9375, -3.8228258073]]),
                 23., 47., 10, id="duplicate index - 10 quantiles"),
    pytest.param(duplicate_index_with_nan(),
                 pd.DataFrame([[24.0625, -7.0899265361], [26.5625, 3.0395129137],
                               [29.0625, 3.6049946383], [31.5625, -6.7375832739],
                               [34.25, -3.6006797089], [36.25, -3.6458372785],
                               [38.4375, -8.7002223092], [40.9375, 1.0519837867],
                               [43.4375, 5.4893416501], [45.9375, -3.8228258073]]),
                 23., 47., 10, id="duplicate index with nan - 10 quantiles"),
    pytest.param(pd.DataFrame([[2.0, [1.0, 10.0]], [2.2, [2.0, 20.0]], [2.4, [3.0, 30.0]], [2.6, [4.0, 40.0]]]),
                 HTTPException(status_code=422),
                 2.2, 2.6, 2,
                 id="double array"),
    pytest.param(pd.DataFrame([[2.0, [1.0, 10.0]], [2.2, np.NaN], [2.4, [2.0, 20.0]], [2.6, [3.0, 30.0]]]),
                 HTTPException(status_code=422),
                 2.2, 2.6, 2,
                 id="double array with nan"),
    pytest.param(pd.DataFrame([[2.0, "ZONE 1"], [2.2, "Zone 2"], [2.4, "ZONE 3"], [2.6, "ZONE 4"]]),
                 HTTPException(status_code=422),
                 2.2, 2.6, 2,
                 id="text"),
    pytest.param(pd.DataFrame([[2.0, "ZONE 1"], [2.2, np.NaN], [2.4, "ZONE 2"], [2.6, "ZONE 3"]]),
                 HTTPException(status_code=422),
                 2.2, 2.6, 2,
                 id="text with nan"),
    pytest.param(pd.DataFrame([[2.0, ["ZONE 1", "AAA"]], [2.2, ["ZONE 2", "BBB"]], [2.4, ["ZONE 3", ]]]),
                 HTTPException(status_code=422),
                 2.2, 2.6, 2,
                 id="text array"),
    pytest.param(pd.DataFrame([[2.0, ["ZONE 1", "AAA"]], [2.2, np.NaN], [2.4, ["ZONE 3", ]]]),
                 HTTPException(status_code=422),
                 2.2, 2.6, 2,
                 id="text array with NaN"),
    pytest.param(pd.DataFrame([1.2, 1.5, 2.3, 2.4, 4.6, 5.8]),
                 HTTPException(status_code=400),
                 2.2, 2.6, 2,
                 id="data with one column, bulk data must have an index"),
    pytest.param(pd.DataFrame([[2.0], [2.2], [2.4], [2.6]]),
                 HTTPException(status_code=400),
                 2.2, 2.6, 2,
                 id="data with one column, bulk data must have an index"),
]
decimated_log_data_orient = 'split'


@pytest.mark.parametrize("nan_conversion", [pytest.param(True, id="nan_string"),
                                            pytest.param(False, id="native_nan")])
@pytest.mark.parametrize("decimated_test_data, expected_result, start, stop, quantile", decimated_log_data)
def test_decimated_logs(client, decimated_test_data, expected_result, start, stop, quantile, nan_conversion):
    # given
    record = TestHelper.make_minimal_log_record('test_decimated_logs', id='1337')
    TestHelper.post_record_to_storage(record)
    content = decimated_test_data
    if nan_conversion:
        content = content.fillna("NaN")
    content = content.to_json(orient='split')

    response = client.post(TestHelper.build_url('/logs/1337/data?orient=' + decimated_log_data_orient),
                          content,
                          headers=TestHelper.BASE_HEADERS)

    assert response.status_code == 200
    store_response = CreateUpdateRecordsResponse.parse_raw(response.content)
    assert store_response.record_count == 1
    assert store_response.record_ids[0] == '1337'

    # when read decimated
    actual = TestHelper.get_record_from_storage('1337')
    bulk_id = TestHelper.get_bulk_id_from_record(actual)
    assert bulk_id

    params = {'quantiles': quantile}
    if start is not None:
        params.update({'start': start})
    if stop is not None:
        params.update({'stop': stop})
    response = client.get(TestHelper.build_url('/logs/1337/decimated?orient=values'), #  + decimated_log_data_orient),
                          params=params,
                          headers=TestHelper.BASE_HEADERS)
    data = response.content
    if isinstance(expected_result, HTTPException):
        assert response.status_code == expected_result.status_code
    else:
        assert response.status_code == 200
        actual_df = pd.read_json(data, orient="values").replace("NaN", np.NaN)
        pd.testing.assert_frame_equal(expected_result, actual_df)
