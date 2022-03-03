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
import mock
import pytest
import uuid

import pandas as pd
from pandas.util.testing import assert_frame_equal

from fastapi import Header

from app.routers.ddms_v2.log_ddms_v2 import (_write_log_data,
                                             get_persistence,
                                             _get_log_data)

from app.clients.storage_service_client import StorageRecordServiceClient

from app.helper import traces
from app.auth.auth import require_opendes_authorized_user
from app.middleware import require_data_partition_id
from app.wdms_app import wdms_app, app_injector
from app.context import Context
from app.routers.record_utils import fetch_record, update_records
from tests.unit.test_utils import create_mock_class, ctx_fixture

from odes_storage.models import CreateUpdateRecordsResponse, Record

data_partition_id = 'test_partition'

log_payload = {
    "acl": {
        "owners": [
            "data.default.owners@opendes.p4d.cloud.slb-ds.com"
        ],
        "viewers": [
            "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
        ]
    },
    "legal": {
        "legaltags": [
            "opendes-public-usa-dataset-1"
        ],
        "otherRelevantDataCountries": ["US", "FR"],
        "status": None
    },
    "kind": f"{data_partition_id}:wks:log:1.0.5",
    "data": {
        "name": f"{os.path.basename(__file__)}"
    }
}


StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)


@pytest.fixture
def with_test_setup(ctx_fixture):
    async def bypass_authorization():
        # empty method
        pass

    async def set_default_partition(data_partition_id: str = Header('opendes')):
        Context.set_current_with_value(partition_id=data_partition_id)

    async def build_mock_storage():
        return StorageRecordServiceClientMock()

    app_injector.register(StorageRecordServiceClient, build_mock_storage)

    # override authentication dependency
    previous_overrides = wdms_app.dependency_overrides

    try:
        wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        Context.set_current_with_value(app_injector=app_injector)
        yield
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


@pytest.fixture
def mock_persistence():
    class MockPersistence:

        def __init__(self):
            self.dataframe = None
            self.id = None

        async def read_bulk(self, ctx, record: Record, bulk_id_path: str) -> pd.DataFrame:
            return self.dataframe

        async def write_bulk(self, ctx, dataframe) -> str:
            self.dataframe = dataframe
            self.id = str(uuid.uuid4())
            return self.id

    mock = MockPersistence()

    async def override_get_persistence():
        return mock

    previous_overrides = wdms_app.dependency_overrides

    try:
        wdms_app.dependency_overrides[get_persistence] = override_get_persistence
        yield mock
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.mark.asyncio
async def test_fetch_record(with_test_setup):
    expected_record = Record.parse_obj(log_payload)
    moc_get_record = mock.AsyncMock(return_value=expected_record)
    moc_get_record_version = mock.AsyncMock(return_value=expected_record)
    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc_get_record):
        with mock.patch.object(StorageRecordServiceClientMock, 'get_record_version', moc_get_record_version):

            computed_record = await fetch_record(ctx=Context.set_current_with_value(partition_id=data_partition_id),
                                                 record_id="132")

            assert computed_record == expected_record
            moc_get_record.assert_called_with(id="132", data_partition_id=data_partition_id)
            moc_get_record_version.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_record_version(with_test_setup):
    expected_record = Record.parse_obj(log_payload)
    moc_get_record = mock.AsyncMock(return_value=expected_record)
    moc_get_record_version = mock.AsyncMock(return_value=expected_record)
    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc_get_record):
        with mock.patch.object(StorageRecordServiceClientMock, 'get_record_version', moc_get_record_version):

            computed_record = await fetch_record(ctx=Context.set_current_with_value(partition_id=data_partition_id),
                                                 record_id="132", version="1")

            assert computed_record == expected_record
            moc_get_record_version.assert_called_with(id="132", data_partition_id=data_partition_id, version="1")
            moc_get_record.assert_not_called()


@pytest.mark.asyncio
async def test_update_records(with_test_setup):
    expected_response = CreateUpdateRecordsResponse(record_count=2, record_ids=["1", "2"], skipped_record_ids=["1"])
    moc = mock.AsyncMock(return_value=expected_response)

    with mock.patch.object(StorageRecordServiceClientMock, 'create_or_update_records', moc):
        record = Record.parse_obj(log_payload)
        computed_response = await update_records(ctx=Context.set_current_with_value(partition_id=data_partition_id),
                                                 records=[record])

        assert computed_response == expected_response
        moc.assert_called_with(record=[record], data_partition_id=data_partition_id)


@pytest.mark.asyncio
async def test_write_log_data(with_test_setup, mock_persistence):
    expected_response = CreateUpdateRecordsResponse(record_count=2, record_ids=["1", "2"], skipped_record_ids=["1"])

    expected_record = Record.parse_obj(log_payload)
    get_record_moc = mock.AsyncMock(return_value=expected_record)
    create_or_update_records_moc = mock.AsyncMock(return_value=expected_response)

    data = pd.DataFrame.from_dict({'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']})

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', get_record_moc):
        with mock.patch.object(StorageRecordServiceClientMock, 'create_or_update_records',
                               create_or_update_records_moc):

            computed_response = await _write_log_data(
                ctx=Context.set_current_with_value(partition_id=data_partition_id),
                persistence=mock_persistence,
                logid="1234",
                bulk_path=None,
                dataframe=data)

            assert computed_response == expected_response
            get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id)
            create_or_update_records_moc.assert_called_once_with(record=[expected_record],
                                                                 data_partition_id=data_partition_id)
            assert_frame_equal(mock_persistence.dataframe, data)


@pytest.mark.asyncio
async def test_write_log_data_with_bulk_path(with_test_setup, mock_persistence):
    expected_response = CreateUpdateRecordsResponse(record_count=2, record_ids=["1", "2"], skipped_record_ids=["1"])

    expected_record = Record.parse_obj(log_payload)
    expected_record.data["custom_bulkid"] = "default"
    get_record_moc = mock.AsyncMock(return_value=expected_record)
    create_or_update_records_moc = mock.AsyncMock(return_value=expected_response)

    data = pd.DataFrame.from_dict({'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']})

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', get_record_moc):
        with mock.patch.object(StorageRecordServiceClientMock, 'create_or_update_records', create_or_update_records_moc):
            computed_response = await _write_log_data(
                ctx=Context.set_current_with_value(partition_id=data_partition_id),
                persistence=mock_persistence,
                logid="1234",
                bulk_path="data.custom_bulkid",
                dataframe=data)

            assert computed_response == expected_response
            get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id)
            create_or_update_records_moc.assert_called_once_with(record=[expected_record],
                                                                 data_partition_id=data_partition_id)
            assert_frame_equal(mock_persistence.dataframe, data)


@pytest.mark.asyncio
async def test_get_log_data(with_test_setup, mock_persistence):
    expected_record = Record.parse_obj(log_payload)
    expected_data = {'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']}

    get_record_moc = mock.AsyncMock(return_value=expected_record)
    mock_persistence.dataframe = pd.DataFrame.from_dict(expected_data)

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', get_record_moc):

        computed_response = await _get_log_data(
            ctx=Context.set_current_with_value(partition_id=data_partition_id),
            persistence=mock_persistence,
            logid="1234",
            version=None,
            orient="columns",
            bulk_id_path=None)

        get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id)

        assert computed_response.status_code == 200
        assert computed_response.body == b'{"col_1":{"0":3,"1":2,"2":1,"3":0},"col_2":{"0":"a","1":"b","2":"c","3":"d"}}'
        assert computed_response.media_type == 'application/json'


@pytest.mark.asyncio
async def test_get_log_data_with_bulk_path(with_test_setup, mock_persistence):
    expected_record = Record.parse_obj(log_payload)
    expected_record.data["custom_bulkid"] = "424242"
    expected_data = {'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']}

    get_record_moc = mock.AsyncMock(return_value=expected_record)
    mock_persistence.dataframe = pd.DataFrame.from_dict(expected_data)

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', get_record_moc):

        computed_response = await _get_log_data(
            ctx=Context.set_current_with_value(partition_id=data_partition_id),
            persistence=mock_persistence,
            logid="1234",
            version=None,
            orient="columns",
            bulk_id_path="data.custom_bulkid")

        get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id)

        assert computed_response.status_code == 200
        assert computed_response.body == b'{"col_1":{"0":3,"1":2,"2":1,"3":0},"col_2":{"0":"a","1":"b","2":"c","3":"d"}}'
        assert computed_response.media_type == 'application/json'


